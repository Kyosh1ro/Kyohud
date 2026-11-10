"""Temporary E profiling: real runtime, deterministic clocks, no timing claims.

Native timings can only be collected in PAYDAY 2. These tests exercise the
capture/report lifecycle, accounting and preservation of the real renderer.
"""
import unittest

from test_hud_e_native_replacement import _radial_runtime


def _diagnostic_runtime():
    lua = _radial_runtime()
    lua.execute('''
        -- The composed fixture mounts without a native Application clock.
        -- Start this capture after installing deterministic clock bindings.
        R._perf_done, R._perf_diagnostic = nil, nil
        R._perf_report, R._perf_result = nil, nil
        perf_wall = 0
        perf_cpu = 0
        perf_clock_reads = 0
        perf_reports = {}
        Application = {time = function() return perf_wall end}
        os.clock = function()
            perf_clock_reads = perf_clock_reads + 1
            return perf_cpu
        end
        log = function(message) perf_reports[#perf_reports + 1] = message end
        local player = R._coordinate_player
        R._coordinate_player = function(self, ...)
            perf_cpu = perf_cpu + 0.001
            return player(self, ...)
        end
        local crew = R._coordinate_crew
        R._coordinate_crew = function(self, ...)
            perf_cpu = perf_cpu + 0.003
            return crew(self, ...)
        end
        function perf_step(wall)
            perf_wall = wall
            R:update(m, 100 + wall, 0.1)
        end
    ''')
    return lua


class PerformanceDiagnosticTests(unittest.TestCase):
    def test_loading_without_a_player_does_not_consume_the_capture(self):
        lua = _diagnostic_runtime()
        lua.execute('''
            perf_player_unit = managers.player.player_unit
            managers.player.player_unit = function() return nil end
            for i = 0, 300 do perf_step(i / 10) end
        ''')
        self.assertEqual(len(lua.globals().perf_reports), 0)
        self.assertEqual(lua.globals().perf_clock_reads, 0)
        lua.execute('''
            managers.player.player_unit = perf_player_unit
            perf_step(31); perf_step(35.9)
        ''')
        self.assertEqual(lua.globals().perf_clock_reads, 0)
        lua.execute("perf_step(36)")
        self.assertEqual(lua.globals().R._perf_diagnostic.frames, 1)

    def test_warmup_and_real_update_interval_buckets(self):
        lua = _diagnostic_runtime()
        lua.execute("perf_step(0); perf_step(4.999)")
        self.assertEqual(lua.globals().perf_clock_reads, 0)
        self.assertEqual(len(lua.globals().perf_reports), 0)
        lua.execute("perf_step(5); perf_step(5.01); perf_step(5.03); perf_step(5.07); perf_step(5.13)")
        state = lua.globals().R._perf_diagnostic
        self.assertEqual(state.frames, 5)
        self.assertAlmostEqual(state.gap_sum, 0.13, places=8)
        self.assertAlmostEqual(state.gap_max, 0.06, places=8)
        self.assertEqual((state.over16, state.over33, state.over50), (3, 2, 1))
        self.assertEqual(len(lua.globals().perf_reports), 0)

    def test_flat_clock_is_reported_as_inconclusive_not_free_work(self):
        lua = _diagnostic_runtime()
        lua.execute('''
            os.clock = function() return 0 end
            for i = 0, 300 do perf_step(i / 10) end
        ''')
        report = lua.globals().perf_reports[1]
        self.assertIn("COMPLETE", report)
        self.assertIn("zero non concluant", report)
        self.assertEqual(lua.globals().R._perf_result.metrics.runtime.total, 0)
        self.assertGreater(lua.globals().R._perf_result.metrics.runtime.calls, 100)

    def test_bad_clock_results_or_exceptions_do_not_break_rendering(self):
        for clock in ("Application.time", "os.clock"):
            for body in ("return nil", "return 0/0", "return math.huge", "error('clock failure')"):
                with self.subTest(clock=clock, body=body):
                    lua = _diagnostic_runtime()
                    lua.execute("perf_step(0); perf_step(5)")
                    lua.execute(f"{clock} = function() {body} end; perf_step(5.1)")
                    self.assertEqual(len(lua.globals().perf_reports), 1)
                    self.assertIn("ABORTED", lua.globals().perf_reports[1])
                    self.assertEqual(lua.eval("h:alpha()"), 0)

    def test_native_hud_disable_interrupts_and_does_not_rearm_capture(self):
        lua = _diagnostic_runtime()
        lua.execute("perf_step(0); perf_step(5); R._disabled = true; perf_step(5.1)")
        self.assertEqual(len(lua.globals().perf_reports), 1)
        self.assertIn("INTERRUPTED", lua.globals().perf_reports[1])
        lua.execute("R._disabled = false; for i = 60, 400 do perf_step(i / 10) end")
        self.assertEqual(len(lua.globals().perf_reports), 1)

    def test_heap_snapshots_never_force_a_collection(self):
        lua = _diagnostic_runtime()
        lua.execute('''
            perf_gc_calls = {}
            collectgarbage = function(command)
                perf_gc_calls[#perf_gc_calls + 1] = command
                return #perf_gc_calls * 1024
            end
            for i = 0, 300 do perf_step(i / 10) end
        ''')
        calls = lua.globals().perf_gc_calls
        self.assertEqual([calls[i] for i in range(1, len(calls) + 1)], ["count", "count"])
        self.assertIn("1024.0 -> 2048.0 KiB", lua.globals().perf_reports[1])
        self.assertIn("pas pauses GC", lua.globals().perf_reports[1])

    def test_profiling_enabled_or_disabled_preserves_real_render_and_native_mask(self):
        signatures = []
        for enabled in (True, False):
            lua = _diagnostic_runtime()
            lua.globals().R._perf_enabled = enabled
            lua.execute("for i = 0, 300 do perf_step(i / 10) end")
            expressions = (
                "kyohud.hud.player._root:x()", "kyohud.hud.player._root:y()",
                "kyohud.hud.player._root:w()", "kyohud.hud.player._root:h()",
                "kyohud.hud.player._root:visible()", "kyohud.hud.player:verify()",
                "kyohud.hud.crew._root:x()", "kyohud.hud.crew._root:y()",
                "kyohud.hud.crew._cards[1]._backdrop:y()",
                "kyohud.hud.crew._cards[1]._backdrop:h()",
                "kyohud.hud.crew:_verify_render()",
                "kyohud.hud.player._h5_id_label:text()",
                "kyohud.hud.player._h5_id_label:visible()",
                "h:alpha()", "n:alpha()", "R:_verify_local_backdrop()",
            )
            signatures.append([lua.eval(expr) for expr in expressions])
            self.assertEqual(len(lua.globals().perf_reports), int(enabled))
        self.assertEqual(signatures[0], signatures[1])
        self.assertTrue(signatures[0][5])
        self.assertTrue(signatures[0][10])
        self.assertEqual(signatures[0][13:15], [0, 0])

    def test_backward_clocks_abort_once_without_stopping_the_renderer(self):
        for clock in ("Application", "os.clock"):
            with self.subTest(clock=clock):
                lua = _diagnostic_runtime()
                lua.execute("perf_step(0); perf_root = kyohud.hud.player._root")
                if clock == "Application":
                    lua.execute("perf_step(-1)")
                else:
                    lua.execute("perf_step(5); perf_cpu = -1; perf_step(5.1)")
                self.assertEqual(len(lua.globals().perf_reports), 1)
                self.assertIn("ABORTED", lua.globals().perf_reports[1])
                lua.execute("for i = 60, 70 do perf_step(i / 10) end")
                self.assertEqual(len(lua.globals().perf_reports), 1)
                self.assertTrue(lua.eval("kyohud.hud.player._root == perf_root"))
                self.assertEqual(lua.eval("h:alpha()"), 0)

    def test_bounded_capture_measures_real_paths_once_then_stops_sampling(self):
        lua = _diagnostic_runtime()
        lua.execute('''
            for i = 0, 400 do perf_step(i / 10) end
        ''')
        self.assertEqual(len(lua.globals().perf_reports), 1,
                         "one aggregate report required, never per-frame logging")
        report = lua.globals().perf_reports[1]
        self.assertIn("[KyoHUD][Perf]", report)
        self.assertIn("os.clock", report)
        self.assertLessEqual(len(report.splitlines()), 16)
        result = lua.globals().R._perf_result
        self.assertIsNotNone(result)
        self.assertGreater(result.frames, 100)
        self.assertAlmostEqual(result.metrics.player.total / result.frames,
                               0.001, places=8)
        self.assertAlmostEqual(result.metrics.crew.total / result.frames,
                               0.003, places=8)
        self.assertAlmostEqual(result.metrics.runtime.total / result.frames,
                               0.004, places=8)
        self.assertEqual(result.metrics.native_priority.calls, result.frames)
        self.assertEqual(result.metrics.native_replace.calls, result.frames)
        self.assertEqual(result.metrics.runtime.calls, result.frames)
        lua.execute('''
            perf_reads_after = perf_clock_reads
            perf_saved_player_root = kyohud.hud.player._root
            perf_saved_card = kyohud.hud.crew._cards[1]
            for i = 401, 500 do perf_step(i / 10) end
        ''')
        self.assertEqual(lua.globals().perf_clock_reads,
                         lua.globals().perf_reads_after)
        self.assertEqual(len(lua.globals().perf_reports), 1)
        self.assertTrue(lua.eval("kyohud.hud.player._root == perf_saved_player_root"))
        self.assertTrue(lua.eval("kyohud.hud.crew._cards[1] == perf_saved_card"))


if __name__ == "__main__":
    unittest.main()
