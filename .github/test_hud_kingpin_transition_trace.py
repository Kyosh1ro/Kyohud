"""RED: one real Kingpin ACTIVE -> expiry -> terminal transition must emit the
new production diagnostic timeline [KyoHUD][KingpinTransition].

The single transition is driven through the real native radial setter, the real
throttled runtime update, the real equipment source validation and the real
terminal repair. The test only extracts the already emitted log lines; it does
not record or synthesize timeline records itself.

Current production has no KingpinTransition instrumentation, so the bounded
timeline assertion is expected to fail (RED). The behavioural assertions that
precede it must keep proving that the positive P/E render, the real native hook,
the expiry fallback and the terminal repair all really ran.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua
from test_hud_kingpin_terminal_player import SETUP, SAVE_AND_EXPIRE, TERMINAL
from test_hud_kingpin_trigger_probe import INSTALL_KINGPIN_SENTINEL
from test_hud_residual_probe import (INSTALL_CLOCK_AND_LOG_COUNTERS,
                                     _rearm_with_sentinel)

TRACE_PREFIX = "[KyoHUD][KingpinTransition]"
TRACE_LIMIT = 48
COMMON_FIELDS = (
    "seq", "stage", "t", "anchor", "app", "publication",
    "p_visible", "p_verified", "e_visible",
    "native_parent_visible", "meter_visible", "icon_visible",
)
BOOL_FIELDS = (
    "p_visible", "p_verified", "e_visible",
    "native_parent_visible", "meter_visible", "icon_visible",
)
REQUIRED_STAGES = (
    "last_positive", "source_reject", "release_before", "release_after",
    "priority_hide", "terminal_enter", "terminal_exit", "runtime_state",
)
STATE_TIME_FIELDS = ("seq", "t", "app")


def _transition_lua():
    """Real Kingpin fixture plus the existing sentinel and log helpers."""
    lua = kingpin_lua()
    lua.execute(INSTALL_KINGPIN_SENTINEL)
    lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
    _rearm_with_sentinel(lua)
    return lua


def _transition_lines(lua):
    """Return only the lines already emitted through the real log() wrapper."""
    lua.execute(r'''
        _test_transition_lines = {}
        for _, message in ipairs(log_texts) do
            message = tostring(message)
            if message:find("[KyoHUD][KingpinTransition]", 1, true) then
                _test_transition_lines[#_test_transition_lines + 1] = message
            end
        end
        _test_transition_count = #_test_transition_lines
    ''')
    g = lua.globals()
    count = int(g._test_transition_count)
    return [str(g._test_transition_lines[i]) for i in range(1, count + 1)]


def _transition_count(lua):
    return len(_transition_lines(lua))


def _parse_line(line):
    marker = line.find(TRACE_PREFIX)
    if marker < 0:
        return None
    fields = {}
    for token in line[marker + len(TRACE_PREFIX):].strip().split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = value
    return fields


def _publication(fields):
    raw = fields.get("publication", "")
    if "/" not in raw:
        return None
    left, total = raw.split("/", 1)
    try:
        return float(left), float(total)
    except ValueError:
        return None


def _bool_field(fields, key):
    return fields.get(key) == "true"


class KingpinTransitionTimelineTests(unittest.TestCase):
    def test_one_transition_emits_ordered_bounded_timeline(self):
        lua = _transition_lua()
        g = lua.globals()

        self.assertEqual(int(g._kingpin_opens), 1,
                         "the runtime must probe KYO_KINGPIN_PERF once")
        self.assertEqual(int(g._sentinel_opens), 1,
                         "the runtime must probe KYO_RESIDUAL_PERF once")
        lua.execute(r'''
            local p = kyohud.hud.runtime._residual_probe
            _test_probe_mode = p and p.mode
        ''')
        self.assertEqual(g._test_probe_mode, "kingpin",
                         "the armed probe must select kingpin mode")

        lua.execute(SETUP)
        self.assertTrue(bool(g._pre_p_visible),
                        "precondition: owned player panel must start visible")
        self.assertTrue(bool(g._pre_p_verify),
                        "precondition: owned player panel must start certified")
        lua.execute(r'''
            local p = kyohud.hud.runtime._residual_probe
            _test_probe_inactive = (p ~= nil and p.active == false
                and p.done == false)
            _test_pre_clock = clock_reads
        ''')
        self.assertIs(g._test_probe_inactive, True,
                      "the kingpin probe must start inactive")
        self.assertEqual(int(g._test_pre_clock), 0,
                         "inactive kingpin diagnostics must not read os.clock")
        self.assertEqual(_transition_count(lua), 0,
                         "inactive kingpin diagnostics must stay silent")

        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(r'''
            _test_pos_p_render_verified = (_P._render_verified == true)
            _test_pos_active = (kyohud.hud.runtime._residual_probe.active == true)
        ''')
        self.assertTrue(bool(g._post_kingpin_e_verify),
                        "positive event must certify the equipment render")
        self.assertTrue(bool(g._post_kingpin_root_visible),
                        "positive event must keep the owned equipment root visible")
        self.assertTrue(bool(g._post_kingpin_row6_visible),
                        "positive event must expose the owned ACTIVE row")
        self.assertEqual(int(g._post_kingpin_set_radial_hooks), 1,
                         "positive event must reach the one real native PostHook")
        self.assertTrue(bool(g._test_pos_p_render_verified),
                        "positive event must preserve the certified P render")
        self.assertIs(g._test_pos_active, True,
                      "the positive native event must arm the kingpin capture")

        lua.execute(r'''
            _app_now = 1005.99
            _m:set_player_ability_radial({current = 0.01, total = 6})
            _test_anchor_app = Application:time()
            _test_anchor_p_verified = (_P._render_verified == true)
            _test_anchor_e_visible = (_E._root ~= nil
                and _E._root:visible() == true)
            _test_anchor_native_parent_visible = (_ability_parent:visible() == true)
            _test_anchor_meter_hidden = (_ability_meter:visible() == false)
            _test_anchor_icon_hidden = (_ability_icon:visible() == false)
        ''')
        self.assertAlmostEqual(float(g._test_anchor_app), 1005.99, places=6,
                               msg="the last positive must observe 1005.99")
        self.assertIs(g._test_anchor_p_verified, True,
                      "the last positive must keep P certified")
        self.assertIs(g._test_anchor_e_visible, True,
                      "the last positive must keep E visible")
        self.assertIs(g._test_anchor_native_parent_visible, True,
                      "the last positive must leave the native parent visible")
        self.assertIs(g._test_anchor_meter_hidden, True,
                      "the last positive must keep the native meter leased")
        self.assertIs(g._test_anchor_icon_hidden, True,
                      "the last positive must keep the native icon leased")

        lua.execute(SAVE_AND_EXPIRE)
        self.assertIs(g._expiry_p_hidden, True,
                      "expiry fallback must keep the owned P panel hidden")
        self.assertIs(g._expiry_native_parent_visible, True,
                      "expiry fallback must leave the native parent visible")
        self.assertIs(g._expiry_leaves_visible, True,
                      "expiry fallback must restore the native ability leaves")
        lua.execute(r'''
            _test_expiry_p_ran = (_P._update_ran_now == true)
            _test_expiry_e_ran = (_E._update_ran_now == true)
            _test_expiry_parent_visible = (_ability_parent:visible() == true)
        ''')
        self.assertIs(g._test_expiry_parent_visible, True,
                      "expiry diagnostics must never mutate the native parent")

        lua.execute("_R:update(_m, 3.22, 0.01)")
        first_stable_count = _transition_count(lua)
        lua.execute(r'''
            _test_stable_parent_visible = (_ability_parent:visible() == true)
            _R:update(_m, 3.22, 0.01)
            _test_stable2_parent_visible = (_ability_parent:visible() == true)
        ''')
        second_stable_count = _transition_count(lua)
        self.assertIs(g._test_stable_parent_visible, True,
                      "stable throttled diagnostics must not mutate the native parent")
        self.assertIs(g._test_stable2_parent_visible, True,
                      "repeated stable diagnostics must not mutate the native parent")
        self.assertEqual(second_stable_count, first_stable_count,
                         "runtime_state must deduplicate stable throttled frames")

        lua.execute(TERMINAL)
        self.assertIs(g._final_p_visible, True,
                      "terminal zero must restore the owned P panel synchronously")
        self.assertIs(g._final_p_verify, True,
                      "terminal zero must certify the restored P panel")
        self.assertIs(g._final_e_visible, True,
                      "terminal zero must keep the equipment panel visible")
        self.assertIs(g._final_native_parent_hidden, True,
                      "terminal zero must hide the native radial parent")
        self.assertIs(g._final_leaves_visible, True,
                      "terminal zero must restore the native ability leaves")
        self.assertIs(g._final_same_root, True,
                      "terminal zero must reuse the same player root")
        self.assertIs(g._final_same_gauge, True,
                      "terminal zero must reuse the same player gauge")

        lua.execute("_R:update(_m, 23.4, 0.05)")
        lua.execute(r'''
            local p = kyohud.hud.runtime._residual_probe
            _test_finish_done = (p ~= nil and p.done == true)
            _test_finish_active = (p ~= nil and p.active == true)
            _test_finish_clock = clock_reads
        ''')
        finish_count = _transition_count(lua)
        self.assertIs(g._test_finish_done, True,
                      "20s of kingpin capture must finish the probe")
        self.assertIs(g._test_finish_active, False,
                      "a finished kingpin probe must be inactive")

        lua.execute(r'''
            _m:set_player_ability_radial({current = 6, total = 6})
            _R:update(_m, 23.5, 0.05)
            _test_post_clock = clock_reads
        ''')
        post_count = _transition_count(lua)
        self.assertEqual(post_count, finish_count,
                         "a completed kingpin trace must stay silent")
        self.assertEqual(int(g._test_post_clock), int(g._test_finish_clock),
                         "a completed kingpin trace must not read os.clock")

        lines = _transition_lines(lua)
        self.assertGreaterEqual(
            len(lines), 1,
            "RED: one Kingpin transition must emit [KyoHUD][KingpinTransition] "
            "stage records")
        self.assertLessEqual(len(lines), TRACE_LIMIT,
                             "the Kingpin transition trace must be bounded")

        records = []
        for line in lines:
            fields = _parse_line(line)
            self.assertIsNotNone(fields,
                                 "every emitted line must carry the transition prefix")
            records.append(fields)

        parsed = []
        for index, fields in enumerate(records):
            missing = [key for key in COMMON_FIELDS if key not in fields]
            self.assertFalse(missing,
                             "record %d missing fields %s" % (index, missing))
            anchor = fields["anchor"]
            self.assertIn("last", anchor.lower(),
                          "runtime time must be explicitly anchored")
            self.assertIn("validated", anchor.lower(),
                          "runtime time must cite the last validated update")
            self.assertIn("update", anchor.lower(),
                          "runtime time must cite the last validated update")
            try:
                seq = int(fields["seq"])
                runtime_t = float(fields["t"])
                app = float(fields["app"])
            except (TypeError, ValueError):
                self.fail("record %d has non-numeric seq/t/app" % index)
            publication = _publication(fields)
            self.assertIsNotNone(publication,
                                 "record %d must expose publication remaining/total"
                                 % index)
            for key in BOOL_FIELDS:
                self.assertIn(fields[key], ("true", "false"),
                              "record %d field %s must be a real boolean"
                              % (index, key))
            if fields["stage"] == "runtime_state":
                self.assertIn("p_ran", fields)
                self.assertIn("e_ran", fields)
                self.assertIn(fields["p_ran"], ("true", "false"))
                self.assertIn(fields["e_ran"], ("true", "false"))
            if fields["stage"] == "source_reject":
                self.assertEqual(fields.get("reason"), "upgrade_inactive",
                                 "source_reject must expose the upgrade_inactive reason")
            parsed.append((fields, runtime_t, app, seq, publication))

        seqs = [item[3] for item in parsed]
        self.assertTrue(all(seqs[i] > seqs[i - 1] for i in range(1, len(seqs))),
                        "seq must strictly increase across the bounded timeline")

        positions = {}
        for index, item in enumerate(parsed):
            positions.setdefault(item[0]["stage"], []).append(index)
        missing_stages = [stage for stage in REQUIRED_STAGES
                          if stage not in positions]
        self.assertFalse(missing_stages,
                         "missing transition stages %s" % (missing_stages,))

        source_reject_index = positions["source_reject"][0]
        last_positive_candidates = [index for index in positions["last_positive"]
                                    if index < source_reject_index]
        self.assertTrue(last_positive_candidates,
                        "last_positive must precede source_reject")
        last_positive_index = last_positive_candidates[-1]

        release_before_candidates = [index for index in positions["release_before"]
                                     if index > source_reject_index]
        self.assertTrue(release_before_candidates,
                        "source_reject must precede release_before")
        release_before_index = release_before_candidates[0]

        release_after_candidates = [index for index in positions["release_after"]
                                    if index > release_before_index]
        self.assertTrue(release_after_candidates,
                        "release_before must precede release_after")
        release_after_index = release_after_candidates[0]

        priority_hide_candidates = [index for index in positions["priority_hide"]
                                    if index > release_after_index]
        self.assertTrue(priority_hide_candidates,
                        "release_after must precede priority_hide")
        priority_hide_index = priority_hide_candidates[0]

        terminal_enter_candidates = [index for index in positions["terminal_enter"]
                                     if index > priority_hide_index]
        self.assertTrue(terminal_enter_candidates,
                        "priority_hide must precede terminal_enter")
        terminal_enter_index = terminal_enter_candidates[0]

        terminal_exit_candidates = [index for index in positions["terminal_exit"]
                                    if index > terminal_enter_index]
        self.assertTrue(terminal_exit_candidates,
                        "terminal_enter must precede terminal_exit")
        terminal_exit_index = terminal_exit_candidates[-1]

        last_positive = parsed[last_positive_index]
        self.assertAlmostEqual(
            last_positive[4][0], 0.01, places=6,
            msg="last_positive must retain the actual last current (0.01), "
                "not merely the first 6/6 event")
        self.assertAlmostEqual(last_positive[4][1], 6.0, places=3,
                               msg="last_positive must retain the publication total")
        self.assertAlmostEqual(
            last_positive[2], 1005.99, places=6,
            msg="last_positive must retain Application=1005.99")

        source_reject = parsed[source_reject_index]
        self.assertEqual(source_reject[0].get("reason"), "upgrade_inactive")
        self.assertAlmostEqual(
            source_reject[2], 1006.01, places=6,
            msg="source_reject must observe Application=1006.01")
        self.assertIs(_bool_field(source_reject[0], "p_visible"), True,
                      "source_reject observes P before native priority hides it")

        release_after = parsed[release_after_index]
        self.assertIs(_bool_field(release_after[0], "meter_visible"), True,
                      "release_after must report the native meter restored")
        self.assertIs(_bool_field(release_after[0], "icon_visible"), True,
                      "release_after must report the native icon restored")

        priority_hide = parsed[priority_hide_index]
        self.assertIs(_bool_field(priority_hide[0], "p_visible"), False,
                      "priority_hide must report P hidden by native priority")

        terminal_exit = parsed[terminal_exit_index]
        self.assertIs(_bool_field(terminal_exit[0], "p_visible"), True,
                      "final terminal_exit must report P visible")
        self.assertIs(_bool_field(terminal_exit[0], "p_verified"), True,
                      "final terminal_exit must report P render_verified")
        self.assertIs(_bool_field(terminal_exit[0], "native_parent_visible"), False,
                      "final terminal_exit must report the native parent hidden")
        self.assertIs(_bool_field(terminal_exit[0], "e_visible"), True,
                      "final terminal_exit must report E visible")
        self.assertIs(_bool_field(terminal_exit[0], "meter_visible"), True,
                      "final terminal_exit must report the native meter visible")
        self.assertIs(_bool_field(terminal_exit[0], "icon_visible"), True,
                      "final terminal_exit must report the native icon visible")

        runtime_states = [parsed[index] for index in positions["runtime_state"]]
        self.assertTrue(runtime_states,
                        "runtime_state records must exist")
        expiry_states = [parsed[index] for index in positions["runtime_state"]
                         if last_positive_index < index < terminal_enter_index]
        self.assertTrue(expiry_states,
                        "runtime_state must record the expiry window")
        self.assertTrue(
            any(_bool_field(item[0], "p_ran") == bool(g._test_expiry_p_ran)
                and _bool_field(item[0], "e_ran") == bool(g._test_expiry_e_ran)
                for item in expiry_states),
            "runtime_state p_ran/e_ran must describe the throttled expiry update")

        previous_state = None
        for item in runtime_states:
            state_key = tuple(sorted(
                (key, value) for key, value in item[0].items()
                if key not in STATE_TIME_FIELDS))
            self.assertNotEqual(state_key, previous_state,
                                "runtime_state must deduplicate stable state")
            previous_state = state_key

    def test_invalid_nonzero_then_zero_publishes_real_publication(self):
        lua = _transition_lua()
        g = lua.globals()

        lua.execute(SETUP)
        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(r'''
            _app_now = 1005.99
            _m:set_player_ability_radial({current = 0.01, total = 6})
            _G._pub_p_root = _P._root
        ''')
        lua.execute(r'''
            _m:set_player_ability_radial({current = -0.01, total = 6})
        ''')
        lua.execute(r'''
            _m:set_player_ability_radial({current = 0, total = 6})
            _G._pub_final_p_visible = (_P._root:visible() == true)
            _G._pub_final_p_verify = (_P:verify() == true)
            _G._pub_final_parent_visible = (_ability_parent:visible() == true)
            _G._pub_final_same_root = (_P._root == _G._pub_p_root)
        ''')

        lines = _transition_lines(lua)
        records = [fields for fields in (_parse_line(line) for line in lines)
                   if fields is not None]
        by_stage = {}
        for index, fields in enumerate(records):
            by_stage.setdefault(fields.get("stage"), []).append((index, fields))

        rejected = by_stage.get("publication_rejected", [])
        self.assertTrue(rejected,
                        "RED: an invalid nonzero native publication must emit "
                        "publication_rejected")

        reject_index, reject_fields = rejected[0]
        reject_publication = _publication(reject_fields)
        self.assertIsNotNone(reject_publication,
                             "publication_rejected must expose a remaining/total")
        self.assertAlmostEqual(reject_publication[0], -0.01, places=6,
                               msg="publication_rejected must retain the real "
                                   "-0.01 remaining, not an invented value")
        self.assertAlmostEqual(reject_publication[1], 6.0, places=3,
                               msg="publication_rejected must retain total=6")
        self.assertFalse(
            any(fields.get("stage") == "terminal_enter"
                and _publication(fields) == reject_publication
                for _, fields in by_stage.get("terminal_enter", [])),
            "the invalid nonzero publication must never be labeled terminal_enter")

        positives = [item for item in by_stage.get("last_positive", [])
                     if item[0] < reject_index]
        self.assertTrue(positives, "last_positive must precede publication_rejected")
        last_publication = _publication(positives[-1][1])
        self.assertIsNotNone(last_publication,
                             "last_positive must expose a remaining/total")
        self.assertAlmostEqual(last_publication[0], 0.01, places=6,
                               msg="last_positive must retain the actual .01 "
                                   "remaining before rejection")
        self.assertAlmostEqual(last_publication[1], 6.0, places=3,
                               msg="last_positive must retain total=6")

        terminal = by_stage.get("terminal_enter", [])
        self.assertTrue(terminal,
                        "RED: the following native zero must emit terminal_enter")
        enter_index, enter_fields = terminal[-1]
        self.assertGreater(enter_index, reject_index,
                           "terminal_enter must follow publication_rejected")
        enter_publication = _publication(enter_fields)
        self.assertIsNotNone(enter_publication,
                             "terminal_enter must expose a remaining/total")
        self.assertAlmostEqual(enter_publication[0], 0.0, places=6,
                               msg="terminal_enter must report remaining=0")
        self.assertAlmostEqual(enter_publication[1], 6.0, places=3,
                               msg="terminal_enter must report exact total=6, "
                                   "never an invented 0/1")

        exits = [item for item in by_stage.get("terminal_exit", [])
                 if item[0] >= enter_index]
        self.assertTrue(exits,
                        "RED: terminal zero must emit terminal_exit")
        exit_publication = _publication(exits[-1][1])
        self.assertIsNotNone(exit_publication,
                             "terminal_exit must expose a remaining/total")
        self.assertAlmostEqual(exit_publication[0], 0.0, places=6,
                               msg="terminal_exit must report remaining=0")
        self.assertAlmostEqual(exit_publication[1], 6.0, places=3,
                               msg="terminal_exit must report exact total=6, "
                                   "never an invented 0/1")

        self.assertIs(g._pub_final_same_root, True,
                      "the same owned P root must survive the transition")
        self.assertIs(g._pub_final_p_visible, True,
                      "the final P panel must be visible after native zero")
        self.assertIs(g._pub_final_p_verify, True,
                      "the final P panel must be certified after native zero")
        self.assertIs(g._pub_final_parent_visible, False,
                      "the native parent must be hidden at native zero")


class KingpinTransitionGateTests(unittest.TestCase):
    def test_trace_is_silent_when_off_or_in_general_mode(self):
        for scenario in ("off", "general"):
            with self.subTest(scenario=scenario):
                lua = kingpin_lua()
                lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
                if scenario == "general":
                    _rearm_with_sentinel(lua)

                lua.execute(SETUP)
                lua.execute(KINGPIN_ACTIVATE)
                lua.execute(r'''
                    _app_now = 1005.99
                    _m:set_player_ability_radial({current = 0.01, total = 6})
                ''')
                lua.execute(SAVE_AND_EXPIRE)
                lua.execute(TERMINAL)
                lua.execute("_R:update(_m, 23.4, 0.05)")

                g = lua.globals()
                self.assertEqual(
                    _transition_count(lua), 0,
                    "%s: [KyoHUD][KingpinTransition] must only exist in an "
                    "active kingpin capture" % scenario)
                if scenario == "off":
                    self.assertEqual(int(g.clock_reads), 0,
                                     "off: no diagnostic os.clock read may occur")


if __name__ == "__main__":
    unittest.main()
