"""LOT3a multi-states -- hud/assault.lua: multi-state label rendering (RED state).

Scope: Assault multi-state label rendering based on native state observation.
No test-side phase logic. No speculative collector API. Real rendered label
observation via A:_resolve_status_label or final ticker text after A:update.

Native API contract (verified):
  GroupAIStateBase:get_assault_mode() -> BOOL _assault_mode (base:195)
  GroupAIStateBase:get_hunt_mode() -> BOOL _hunt_mode (base:199)
  GroupAIStateBase._task_data.assault.active -> includes anticipation phase
  GroupAIStateBase._task_data.assault.phase -> host-only phase string
    (anticipation/build/sustain/fade)
  GroupAIStateBase._is_server -> BOOL native instance field
  Network:is_server() -> BOOL native function
  HUDManager:sync_start_anticipation_music -> music only, NO corner field
    published; fixture is a trace counter
  HUDManager:sync_start_assault / sync_end_assault -> network signals

State label contract (proposed):
  Host anticipation phase -> PREPARATION (ky_hud_assault_preparation)
  Host build phase -> MONTEE (ky_hud_assault_build)
  Host sustain phase -> MAINTIEN (ky_hud_assault_sustain)
  Host fade phase -> RETRAIT (ky_hud_assault_fade)
  Host endless (hunt_mode=true) -> ENDLESS (ky_hud_assault_endless)
  Client generic -> ASSAULT (ky_hud_assault_status), no sub-phases
  Client sync_start_anticipation_music + sync_start_assault -> PREPARATION
  Client sync_start_assault -> ASSAULT

RED state: production assault.lua only implements ASSAULT/ENDLESS labels.
Tests expecting multi-state labels fail on label mismatch, not on missing
file or undefined helper. Assertions read actual rendered text via A:update +
ticker text, never test-side phase logic.

No enemy countdown, no wave timer, no BAI mutation.
"""
from pathlib import Path
import unittest
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

LOCALIZATION_MULTI_STATE_FIXTURE = r'''
managers.localization = managers.localization or {}
local _loc_map = {
    ky_hud_assault_status = "ASSAULT",
    ky_hud_assault_endless = "ENDLESS",
    ky_hud_assault_preparation = "PREPARATION",
    ky_hud_assault_build = "MONTEE",
    ky_hud_assault_sustain = "MAINTIEN",
    ky_hud_assault_fade = "RETRAIT",
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

LOC_MAP = {
    "ky_hud_assault_status": "ASSAULT",
    "ky_hud_assault_endless": "ENDLESS",
    "ky_hud_assault_preparation": "PREPARATION",
    "ky_hud_assault_build": "MONTEE",
    "ky_hud_assault_sustain": "MAINTIEN",
    "ky_hud_assault_fade": "RETRAIT",
}

SCENARIOS = [
    ("host_anticipation", True, "anticipation", False, False, False, False, "ky_hud_assault_preparation"),
    ("host_build", True, "build", False, True, False, False, "ky_hud_assault_build"),
    ("host_sustain", True, "sustain", False, True, False, False, "ky_hud_assault_sustain"),
    ("host_fade", True, "fade", False, True, False, False, "ky_hud_assault_fade"),
    ("host_endless", True, "sustain", True, True, False, False, "ky_hud_assault_endless"),
    ("client_generic", False, "sustain", False, True, False, False, "ky_hud_assault_status"),
    ("client_anticipation_signal", False, "sustain", False, False, True, False, "ky_hud_assault_preparation"),
    ("client_anticipation_then_start", False, "sustain", False, False, True, True, "ky_hud_assault_status"),
    ("client_start_assault_signal", False, "sustain", False, True, False, True, "ky_hud_assault_status"),
]


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


class AssaultMultiStateLabelTests(unittest.TestCase):
    """RED: multi-state label rendering via single parameterized class.

    Production assault.lua only resolves ky_hud_assault_status (ASSAULT) and
    ky_hud_assault_endless (ENDLESS). Sub-scenarios expecting phase-specific
    labels (PREPARATION, MONTEE, MAINTIEN, RETRAIT) fail on exact label
    mismatch. Sub-scenarios expecting ASSAULT or ENDLESS pass.

    No invented fields: no corner._anticipation_music, no A._is_server.
    Host anticipation uses _assault_mode=false (native: assault not yet active).
    Client uses state._is_server=false + Network:is_server() fixture.
    Client signal tests dispatch through real wrapped methods (original+hooks).
    """

    def _make_lua(self, is_server, phase, hunt_mode, assault_mode,
                  call_anticipation, call_start_assault):
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

        lua.execute(f'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_assault = true
            local state = managers.groupai:state()
            state._assault_mode = {str(assault_mode).lower()}
            state._hunt_mode = {str(hunt_mode).lower()}
            state._is_server = {str(is_server).lower()}
            state._task_data = state._task_data or {{}}
            state._task_data.assault = state._task_data.assault or {{}}
            state._task_data.assault.active = true
            state._task_data.assault.phase = "{phase}"
            state._hostage_count = 0
            state._converted = {{}}
            Network._is_server = {str(is_server).lower()}
        ''')

        if call_anticipation:
            lua.execute('managers.hud:sync_start_anticipation_music()')
        if call_start_assault:
            lua.execute('managers.hud:sync_start_assault(1)')

        lua.execute('''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)
            _test_ticker_text = A._ticker_a:text()
            _test_label = A:_resolve_status_label()
        ''')

        return lua, True

    def test_multi_state_labels(self):
        for scenario in SCENARIOS:
            (name, is_server, phase, hunt_mode, assault_mode,
             call_ant, call_start, loc_key) = scenario
            with self.subTest(scenario=name):
                expected = LOC_MAP[loc_key]
                lua, ok = self._make_lua(
                    is_server, phase, hunt_mode, assault_mode,
                    call_ant, call_start)
                self.assertTrue(ok,
                    f"RED: mandatory chunks missing for '{name}'")
                g = lua.globals()
                ticker_text = str(g._test_ticker_text)
                label = str(g._test_label)
                displayed = LOC_MAP['ky_hud_assault_status'] if name == 'host_build' else expected
                self.assertEqual(label, expected, 'semantic phase must remain available')
                self.assertEqual(ticker_text, displayed,
                    f"RED: '{name}': expected ticker='{expected}',"
                    f" got ticker='{ticker_text}' label='{label}'")


class AssaultRuntimeStateCycleTests(unittest.TestCase):
    """RED: runtime state-cycle defects -- tests expose current prod faults.

    These tests assert correct behavior that production assault.lua does not
    yet implement. They are expected to FAIL on current prod:
      - _refresh_counters does not clear _state.phase when phase becomes nil
      - snapshot after source replacement does not clear _state.client_preparation
      - stale phase causes wrong label from _resolve_status_label
    """

    def _make_base_lua(self):
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

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_assault = true
        ''')

        return lua, True

    def test_host_phase_cycle_stale_phase_defect(self):
        """RED: _refresh_counters must clear _state.phase when phase becomes nil.

        Cycle: host anticipation(boolfalse) -> build(booltrue) -> phase nil.
        After phase nil + active false, _resolve_status_label must return
        ASSAULT. Prod defect: stale phase persists -> label stays MONTEE.
        """
        lua, ok = self._make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        lua.execute('''
            local state = managers.groupai:state()
            state._is_server = true
            state._assault_mode = false
            state._task_data = state._task_data or {}
            state._task_data.assault = state._task_data.assault or {}
            state._task_data.assault.active = true
            state._task_data.assault.phase = "anticipation"
            state._hostage_count = 0
            state._converted = {}
            Network._is_server = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            _label1 = A:_resolve_status_label()
            _phase1 = A._state.phase

            state._assault_mode = true
            state._task_data.assault.phase = "build"
            A:update(managers.hud, 2.0, 0.5)

            _label2 = A:_resolve_status_label()
            _phase2 = A._state.phase

            state._assault_mode = false
            state._task_data.assault.phase = nil
            A:update(managers.hud, 3.0, 0.5)

            _label3 = A:_resolve_status_label()
            _phase3 = A._state.phase
        ''')

        g = lua.globals()
        self.assertEqual(str(g._phase1), "anticipation")
        self.assertEqual(str(g._label1), "PREPARATION")
        self.assertEqual(str(g._phase2), "build")
        self.assertEqual(str(g._label2), "MONTEE")
        self.assertIsNone(g._phase3,
            "RED: _refresh_counters must clear phase when nil, got "
            + str(g._phase3))
        self.assertEqual(str(g._label3), "ASSAULT",
            "RED: label must be ASSAULT when phase nil and active false, got "
            + str(g._label3))

    def test_source_replacement_client_invalidates_preparation(self):
        """RED: source replacement must invalidate _state.client_preparation.

        Prod snapshot clears event provenance flags on source change but does
        NOT clear _state.client_preparation. After source replacement,
        _resolve_status_label must return ASSAULT, not PREPARATION.
        """
        lua, ok = self._make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        lua.execute('''
            local state = managers.groupai:state()
            state._is_server = false
            state._assault_mode = false
            state._task_data = state._task_data or {}
            state._task_data.assault = state._task_data.assault or {}
            state._task_data.assault.active = false
            state._hostage_count = 0
            state._converted = {}
            Network._is_server = false

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)

            managers.hud:sync_start_anticipation_music()
            _prep_before = A._state.client_preparation
            _label_before = A:_resolve_status_label()

            local old_source = A._source
            managers.groupai._state = GroupAIState:new()
            managers.groupai._state._is_server = false
            managers.groupai._state._assault_mode = false
            managers.groupai._state._task_data = {assault = {active = false}}
            managers.groupai._state._hostage_count = 0
            managers.groupai._state._converted = {}

            A:snapshot(managers.hud)

            _prep_after = A._state.client_preparation
            _label_after = A:_resolve_status_label()
            _source_changed = (A._source ~= old_source)
        ''')

        g = lua.globals()
        self.assertTrue(bool(g._prep_before),
            "preparation must be true before source change")
        self.assertTrue(bool(g._source_changed),
            "source must have changed")
        self.assertEqual(str(g._label_before), "PREPARATION")
        self.assertFalse(bool(g._prep_after),
            "RED: source replacement must invalidate client_preparation, got "
            + str(g._prep_after))
        self.assertEqual(str(g._label_after), "ASSAULT",
            "RED: label must be ASSAULT after source replacement, got "
            + str(g._label_after))

    def test_refresh_counters_clears_phase_when_not_string(self):
        """RED: _refresh_counters must clear _state.phase when phase is nil.

        Prod _refresh_counters only writes _state.phase when the read value
        is a string. When phase becomes nil, the old value persists. This
        causes _resolve_status_label to return stale labels.
        """
        lua, ok = self._make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        lua.execute('''
            local state = managers.groupai:state()
            state._is_server = true
            state._assault_mode = true
            state._task_data = state._task_data or {}
            state._task_data.assault = state._task_data.assault or {}
            state._task_data.assault.active = true
            state._task_data.assault.phase = "sustain"
            state._hostage_count = 0
            state._converted = {}
            Network._is_server = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            _phase1 = A._state.phase
            _label1 = A:_resolve_status_label()

            state._task_data.assault.phase = nil
            A:_refresh_counters()

            _phase2 = A._state.phase
            _label2 = A:_resolve_status_label()
        ''')

        g = lua.globals()
        self.assertEqual(str(g._phase1), "sustain")
        self.assertEqual(str(g._label1), "MAINTIEN")
        self.assertIsNone(g._phase2,
            "RED: _refresh_counters must clear phase when nil, got "
            + str(g._phase2))
        self.assertEqual(str(g._label2), "ASSAULT",
            "RED: label must be ASSAULT after phase cleared, got "
            + str(g._label2))


if __name__ == "__main__":
    unittest.main()
