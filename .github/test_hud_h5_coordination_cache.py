"""H5 native-duplicate coordination: stable-update work budgets and cache guards.

Transition under test
---------------------
``RT:update`` calls ``_sync_local_backdrop`` on every recovery pass, which calls
``_coordinate_h5_native_duplicates_unprofiled``. That pass runs at every such
frame even when nothing changed, and today it repeats stable work:

1. ``h5_collect_player_targets`` calls ``ACT:get_actor(slot)`` again (the player
   module also calls it in ``P:_capture_and_render``), and re-certifies the owned
   identity label with fresh getter reads (``text``, ``font_size``,
   ``text_rect``, ``parent``, ``visible``, ``alpha``, ``x/y/w/h``, ``color``).
2. ``ACT.write_crew_native_coverage`` is executed again even though the crew
   module already ran it in ``_present_cards``.
3. The native entry panel ``name`` leaf is reread (``text()`` and ``color()``)
   to build the identity cache key.

The upcoming production optimization memoizes that stable work per generation.
Cache keys must still be refreshed from real snapshots/generations each frame,
and invalidation must happen on source events, acquisition failure and release.
The per-frame ``nv:acquire`` revalidation and the effective root/visibility
reads must never be skipped.

RED today (this file is expected to fail, for the work budgets only)
-------------------------------------------------------------------
* ``ACT:get_actor`` calls per stabilized update: today 2 (player module +
  coordination). GREEN budget after the optimization: exactly 1.
* ``ACT.write_crew_native_coverage`` calls per stabilized update: today 2
  (crew presentation + coordination). GREEN budget: exactly 1.
* Getter reads on ``P._h5_id_label`` per stabilized update are budgeted per
  getter, because only some reads are legitimately kept:
    - ``text``: budget ``<= 1``. This is the fresh cache-key read of the
      identity mirror mandated by review (GLM) to detect in-place corruption.
    - ``visible``: budget ``<= 2``. Two pre-existing guarded visibility passes
      remain: ``_sync_h5_id_label_visibility`` at the end of the coordination
      pass and again at the end of ``_retry_pending_h5_releases`` (called on
      every update).
    - certification getters (``font_size``, ``text_rect``, ``parent``, ``x``,
      ``y``, ``w``, ``h``, ``color``, ``alpha``): budget ``== 0``. A stabilized
      update must not re-certify the cached label; the historic RED was about
      21 certification reads (17 getter reads before the production cache).
* Native ``name`` leaf ``text()``/``color()`` per stabilized update: measured
  as exactly 1 each today (``h5_ensure_local_identity`` reads them once). The
  requested ``>= 2`` RED does not exist in the current production code, so
  these are kept as green guards (``<= 1``) protecting the fresh cache-key read
  the optimization is allowed to keep. The RED is carried by the three budgets
  above.

Guards characterized here (must pass today and after the optimization)
----------------------------------------------------------------------
A. ``NV:acquire`` is revalidated every stabilized update for every held
   group, with the group's own owner, generation and requests table.
B. A held entry panel made dead by the fixture's real ``_alive`` mechanism
   fails closed: the next update releases the group and restores the native
   alpha values; restoring the panel re-collects and re-acquires the exact same
   leaf primitives. The entry panel is used because the real ``h5_child`` index
   already rejects a dead inner leaf (``panel_alive(child)``), so only entry
   invalidation yields the observable whole-group release.
C. A real weapon ammo publication (``RaycastWeaponBase:_native_set_ammo`` on the
   equipped inventory unit, consumed by the genuine ``weapons:refresh`` poll)
   makes the next update pass a fresh ``local_p_w`` target collection while the
   group stays held with the same leaves.
D. Hiding the owned ``P._root`` releases ``local_p_p`` and restores native
   leaves; showing it again re-acquires the same primitives. On that frame the
   player updater is throttled through its real ``_last_update_time`` field,
   because a recovery pass (0.5 s) can legitimately occur while the player
   updater (0.05 s) is throttled; otherwise its in-frame repair would re-show
   the root and the release could never be observed.

Fixture reuse: ``test_hud_local_h5_lifecycle._local_runtime`` (real local
player, weapons and crew consumers; H5 groups acquired after a successful
update). One fresh Lua VM per test, no skip, no expected failure.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_local_h5_lifecycle import _local_runtime


WARM_AND_BASELINE = r'''
    local RT = kyohud.hud.runtime
    local mgr = managers.hud
    _T = 1.1
    for _ = 1, 5 do
        _T = _T + 0.5
        RT:update(mgr, _T, .1)
    end

    _held_crew = false
    _held_pending = false
    for key, state in pairs(RT._h5_groups or {}) do
        if state._release_pending then
            _held_pending = true
        elseif key:sub(1, 5) == "crew_" then
            _held_crew = true
        end
    end

    _baseline_p = (kyohud.hud.player:verify() == true)
    _baseline_c = (kyohud.hud.crew:_verify_render() == true)
    _baseline_w = (kyohud.hud.weapons:verify() == true)
    _baseline_root = kyohud.hud.player._root ~= nil
        and kyohud.hud.player._root:visible() == true
    _baseline_p_group = RT._h5_groups ~= nil
        and RT._h5_groups["local_p_p"] ~= nil
        and not RT._h5_groups["local_p_p"]._release_pending
    _baseline_w_group = RT._h5_groups ~= nil
        and RT._h5_groups["local_p_w"] ~= nil
        and not RT._h5_groups["local_p_w"]._release_pending
    _baseline_label = kyohud.hud.player._h5_id_label ~= nil
        and kyohud.hud.player._h5_identity_verified == true

    function _same_leaf_set(a, b)
        if type(a) ~= "table" or type(b) ~= "table" or #a ~= #b then
            return false
        end
        for i = 1, #a do
            local found = false
            for j = 1, #b do
                if a[i] == b[j] then found = true; break end
            end
            if not found then return false end
        end
        return true
    end
'''


INSTALL_WORK_COUNTERS = r'''
    _wc = _wc or {}
    local wc = _wc
    if not wc.installed then
        wc.installed = true
        wc.saved = {}
        local ACT = kyohud.hud.actors
        local P = kyohud.hud.player
        local NV = kyohud.hud.native_visibility
        local RT = kyohud.hud.runtime
        assert(P._h5_id_label, "identity label must exist before wrapping")
        assert(_LOCAL_NAME, "native entry name leaf must exist before wrapping")

        wc.saved.get_actor = ACT.get_actor
        ACT.get_actor = function(self, ...)
            wc.get_actor = (wc.get_actor or 0) + 1
            return wc.saved.get_actor(self, ...)
        end

        wc.saved.crew_coverage = ACT.write_crew_native_coverage
        ACT.write_crew_native_coverage = function(self, ...)
            wc.crew_coverage = (wc.crew_coverage or 0) + 1
            return wc.saved.crew_coverage(self, ...)
        end

        local label = P._h5_id_label
        wc.saved.label = {}
        wc.label_reads = {}
        for _, name in ipairs({"text", "font_size", "text_rect", "parent",
            "visible", "alpha", "x", "y", "w", "h", "color"}) do
            local original = label[name]
            wc.saved.label[name] = original
            label[name] = function(self, ...)
                wc.label_reads[name] = (wc.label_reads[name] or 0) + 1
                return original(self, ...)
            end
        end

        wc.saved.native_name = {}
        for property, counter in pairs({text = "native_text", color = "native_color"}) do
            local counter_field = counter
            local original = _LOCAL_NAME[property]
            wc.saved.native_name[property] = original
            _LOCAL_NAME[property] = function(self, ...)
                wc[counter_field] = (wc[counter_field] or 0) + 1
                return original(self, ...)
            end
        end

        wc.saved.acquire = NV.acquire
        NV.acquire = function(self, owner, generation, requests)
            local rec = {owner = owner, generation = generation, requests = requests}
            wc.acquire = wc.acquire or {}
            wc.acquire[#wc.acquire + 1] = rec
            wc.acquire_last = wc.acquire_last or {}
            wc.acquire_last[owner] = rec
            return wc.saved.acquire(self, owner, generation, requests)
        end

        function _reset_work_counters()
            wc.get_actor = 0
            wc.crew_coverage = 0
            for name in pairs(wc.saved.label) do
                wc.label_reads[name] = 0
            end
            wc.native_text = 0
            wc.native_color = 0
            wc.acquire = {}
            wc.acquire_last = {}
        end

        function _check_held_acquire()
            local checked = 0
            local missing = ""
            local ok = true
            for key, state in pairs(RT._h5_groups or {}) do
                local relevant = (key == "local_p_p") or (key == "local_p_w")
                    or (key:sub(1, 5) == "crew_")
                if relevant and not state._release_pending then
                    checked = checked + 1
                    local owner = RT._h5_owner .. "_" .. key
                    local rec = wc.acquire_last[owner]
                    if not rec then
                        ok = false
                        missing = missing .. key .. ":missing;"
                    elseif rec.generation ~= state.generation then
                        ok = false
                        missing = missing .. key .. ":generation;"
                    elseif rec.requests ~= state.requests then
                        ok = false
                        missing = missing .. key .. ":requests;"
                    end
                end
            end
            _acquire_ok = ok
            _acquire_checked = checked
            _acquire_missing = missing
        end

        function _export_work_counters()
            _G._m_get_actor = wc.get_actor or 0
            _G._m_crew_coverage = wc.crew_coverage or 0
            local reads = wc.label_reads or {}
            _G._m_label_reads_text = reads.text or 0
            _G._m_label_reads_visible = reads.visible or 0
            local cert = 0
            for _, name in ipairs({"font_size", "text_rect", "parent",
                "x", "y", "w", "h", "color", "alpha"}) do
                cert = cert + (reads[name] or 0)
            end
            _G._m_label_reads_cert = cert
            _G._m_native_text = wc.native_text or 0
            _G._m_native_color = wc.native_color or 0
        end

        function _restore_work_counters()
            if not wc.installed then return end
            ACT.get_actor = wc.saved.get_actor
            ACT.write_crew_native_coverage = wc.saved.crew_coverage
            for name, original in pairs(wc.saved.label) do
                label[name] = original
            end
            for property, original in pairs(wc.saved.native_name) do
                _LOCAL_NAME[property] = original
            end
            NV.acquire = wc.saved.acquire
            wc.installed = false
        end
    end
'''


INSTALL_COORDINATE_OBSERVER = r'''
    _co = _co or {}
    local co = _co
    if not co.installed then
        co.installed = true
        local RT = kyohud.hud.runtime
        co.saved = RT._h5_acquire_group
        RT._h5_acquire_group = function(self, key, targets, source_id, property)
            if key == "local_p_w" then
                co.w_targets = targets
                co.w_calls = (co.w_calls or 0) + 1
            end
            return co.saved(self, key, targets, source_id, property)
        end

        function _co_reset()
            co.w_targets = nil
            co.w_calls = 0
        end

        function _co_restore()
            RT._h5_acquire_group = co.saved
            co.installed = false
        end
    end
'''


def _assert_baseline(testcase, lua):
    g = lua.globals()
    testcase.assertIs(g._baseline_p, True,
                      "positive baseline: player render must verify")
    testcase.assertIs(g._baseline_c, True,
                      "positive baseline: crew render must verify")
    testcase.assertIs(g._baseline_w, True,
                      "positive baseline: weapons render must verify")
    testcase.assertIs(g._baseline_root, True,
                      "positive baseline: the owned player root must be visible")
    testcase.assertIs(g._baseline_p_group, True,
                      "positive baseline: local_p_p must be held")
    testcase.assertIs(g._baseline_w_group, True,
                      "positive baseline: local_p_w must be held")
    testcase.assertIs(g._baseline_label, True,
                      "positive baseline: the local identity must be certified")
    testcase.assertIs(g._held_crew, True,
                      "positive baseline: a crew group must be held")
    testcase.assertIs(g._held_pending, False,
                      "warmup must leave no group in _release_pending")


def _prepare(testcase, lua):
    lua.execute(WARM_AND_BASELINE)
    _assert_baseline(testcase, lua)


class H5CoordinationCacheTests(unittest.TestCase):
    def test_stabilized_update_work_budgets(self):
        """RED: stable updates repeat coordination work that must be cached.

        Known positive first (player/weapons/crew verified, groups held, no
        pending release). Two consecutive recovery passes are measured; the
        second one is asserted. Today ``get_actor`` is 2 and
        ``write_crew_native_coverage`` is 2. Identity label getter reads are
        budgeted per getter: ``text`` ``<= 1`` (fresh cache-key read of the
        mirror), ``visible`` ``<= 2`` (the coordination pass and the
        ``_retry_pending_h5_releases`` pass), and ``== 0`` certification reads
        (``font_size``, ``text_rect``, ``parent``, ``x``, ``y``, ``w``, ``h``,
        ``color``, ``alpha``) — the historic RED was about 21 certification
        reads. The native name leaf is read once for text/color (green guard,
        see module docstring). GREEN budgets after the generation cache: 1, 1,
        text ``<= 1``, visible ``<= 2``, certification ``== 0``, native
        ``<= 1``, ``<= 1``.
        """
        lua = _local_runtime()
        _prepare(self, lua)

        lua.execute(INSTALL_WORK_COUNTERS)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            _reset_work_counters()
            _T = _T + 0.5
            RT:update(mgr, _T, .1)
            _reset_work_counters()
            _T = _T + 0.5
            RT:update(mgr, _T, .1)
            _export_work_counters()
            _restore_work_counters()
        ''')
        g = lua.globals()

        get_actor = int(g._m_get_actor)
        coverage = int(g._m_crew_coverage)
        label_text = int(g._m_label_reads_text)
        label_visible = int(g._m_label_reads_visible)
        label_cert = int(g._m_label_reads_cert)
        native_text = int(g._m_native_text)
        native_color = int(g._m_native_color)

        with self.subTest(budget="ACT:get_actor per stabilized update"):
            self.assertEqual(
                get_actor, 1,
                "a stabilized update must not recall ACT:get_actor from the "
                "H5 coordinator; the player module already captured it, but "
                f"the coordination pass made {get_actor} calls")
        with self.subTest(budget="ACT.write_crew_native_coverage per stabilized update"):
            self.assertEqual(
                coverage, 1,
                "a stabilized update must not rerun crew native coverage; the "
                "crew presentation already published it, but the coordination "
                f"pass made {coverage} calls")
        with self.subTest(budget="identity label text() reads per stabilized update"):
            self.assertLessEqual(
                label_text, 1,
                "a stabilized update may keep at most one fresh text() read of "
                "the identity mirror (cache-key corruption check), but it "
                f"performed {label_text} text() reads")
        with self.subTest(budget="identity label visible() reads per stabilized update"):
            self.assertLessEqual(
                label_visible, 2,
                "a stabilized update may keep the two guarded visible() passes "
                "(coordination end and _retry_pending_h5_releases end), but it "
                f"performed {label_visible} visible() reads")
        with self.subTest(budget="identity label certification getter reads per stabilized update"):
            self.assertEqual(
                label_cert, 0,
                "a stabilized update must not re-certify the cached identity "
                "label (font_size, text_rect, parent, x, y, w, h, color, "
                f"alpha), but it performed {label_cert} certification reads")
        with self.subTest(budget="native name leaf text() per stabilized update"):
            self.assertLessEqual(
                native_text, 1,
                "at most one fresh native name text() read (cache key input) "
                f"is allowed, but {native_text} were observed")
        with self.subTest(budget="native name leaf color() per stabilized update"):
            self.assertLessEqual(
                native_color, 1,
                "at most one fresh native name color() read (cache key input) "
                f"is allowed, but {native_color} were observed")

    def test_signature_buffers_reuse_across_stable_updates(self):
        """RED: every stabilized update allocates a fresh crew signature table.

        Today ``RT:_h5_crew_coverage_signature`` builds ``sig = {}`` plus a new
        ``push`` closure on every update, even when the coordination memo hits
        and ``ACT.write_crew_native_coverage`` is not called again. Three
        stabilized updates therefore use three distinct freshly allocated
        signature tables.

        Observation point. ``RT._h5_coord_cache.crew_sig`` is only written on a
        memo miss (``crew_cache.crew_sig = crew_sig``); on a hit the freshly
        built table is used for the comparison and discarded, so the cached
        field keeps the previous table and cannot reveal the per-update
        allocation. The real contract is the table *used* by the memo
        comparison, so this test wraps the genuine
        ``RT:_h5_crew_coverage_signature`` and records its return value after
        each update (restored before the test ends). The cache-exposed
        ``crew_sig`` identity is still checked as a secondary observable.

        Contract GREEN after the ping-pong buffer production: across three
        stabilized updates the used signature tables come from at most two
        distinct tables (reusable buffers filled in alternation, truncated to
        ``n``); the contents stay equal between consecutive stabilized updates
        (the crew memo remains valid); and the measured update still performs at
        most one ``write_crew_native_coverage`` call. RED today: three distinct
        signature tables.
        """
        lua = _local_runtime()
        _prepare(self, lua)

        lua.execute(INSTALL_WORK_COUNTERS)
        lua.execute(r'''
            _so = _so or {}
            local so = _so
            if not so.installed then
                so.installed = true
                local RT = kyohud.hud.runtime
                so.saved = RT._h5_crew_coverage_signature
                RT._h5_crew_coverage_signature = function(self, ...)
                    local sig = so.saved(self, ...)
                    so.calls = (so.calls or 0) + 1
                    so.last = sig
                    return sig
                end
            end
        ''')
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            _reset_work_counters()
            _so.calls = 0
            _so.last = nil
            _sig_used = {}
            _sig_cached = {}
            for i = 1, 3 do
                if i == 3 then
                    _reset_work_counters()
                end
                _T = _T + 0.5
                RT:update(mgr, _T, .1)
                _sig_used[i] = _so.last
                local cache = RT._h5_coord_cache
                _sig_cached[i] = cache and cache.crew_sig or nil
            end
            _sig_calls = _so.calls or 0
            _export_work_counters()

            local function distinct_count(list)
                local seen, n = {}, 0
                for i = 1, #list do
                    local value = list[i]
                    if value == nil then return -1 end
                    local found = false
                    for j = 1, #seen do
                        if seen[j] == value then found = true; break end
                    end
                    if not found then
                        seen[#seen + 1] = value
                        n = n + 1
                    end
                end
                return n
            end

            _sig_used_distinct = distinct_count(_sig_used)
            _sig_cached_distinct = distinct_count(_sig_cached)
            _sig_used_nonempty = #_sig_used >= 3 and _sig_used[1] ~= nil
                and _sig_used[2] ~= nil and _sig_used[3] ~= nil

            local a, b = _sig_used[2], _sig_used[3]
            _sig_len2 = type(a) == "table" and #a or -1
            _sig_len3 = type(b) == "table" and #b or -1
            _sig_content_equal = false
            _sig_first_diff = 0
            if type(a) == "table" and type(b) == "table"
                and #a == #b then
                _sig_content_equal = true
                for i = 1, #a do
                    if a[i] ~= b[i] then
                        _sig_content_equal = false
                        _sig_first_diff = i
                        break
                    end
                end
            end
        ''')
        g = lua.globals()

        sig_used_nonempty = bool(g._sig_used_nonempty)
        sig_calls = int(g._sig_calls)
        used_distinct = int(g._sig_used_distinct)
        cached_distinct = int(g._sig_cached_distinct)
        sig_len2 = int(g._sig_len2)
        sig_len3 = int(g._sig_len3)
        content_equal = bool(g._sig_content_equal)
        first_diff = int(g._sig_first_diff)
        coverage = int(g._m_crew_coverage)

        lua.execute(r'''
            if _so and _so.installed then
                local RT = kyohud.hud.runtime
                RT._h5_crew_coverage_signature = _so.saved
                _so.installed = false
            end
        ''')
        lua.execute("_restore_work_counters()")

        self.assertIs(
            sig_used_nonempty, True,
            "fixture: the crew coverage signature must be built after each of "
            "the three stabilized updates (a memo hit still builds it for the "
            "comparison)")
        self.assertGreaterEqual(
            sig_calls, 3,
            "fixture: the genuine _h5_crew_coverage_signature must run at least "
            f"once per stabilized update, but only {sig_calls} calls were seen")
        self.assertGreater(
            sig_len2, 0,
            "fixture: the captured signature must carry real content, but its "
            f"length was {sig_len2}")

        with self.subTest(contract="at most two signature tables over three stabilized updates"):
            self.assertLessEqual(
                used_distinct, 2,
                "three stabilized updates must reuse at most two distinct crew "
                "signature tables (ping-pong buffers); today every update "
                "allocates a fresh table, so "
                f"{used_distinct} distinct tables were used")
        with self.subTest(contract="signature contents stable between updates 2 and 3"):
            self.assertIs(
                content_equal, True,
                "the crew coverage signature contents must stay equal between "
                "the second and third stabilized updates even when buffers "
                f"alternate; lengths were {sig_len2} and {sig_len3}, first "
                f"difference at index {first_diff}")
        with self.subTest(contract="crew coverage memo suppresses the second write"):
            self.assertLessEqual(
                coverage, 1,
                "the crew coverage memo must still suppress the coordination "
                "write_crew_native_coverage call while signature buffers "
                f"alternate; the measured update made {coverage} calls")
        with self.subTest(contract="cache-exposed crew signature identity bounded"):
            self.assertGreaterEqual(
                cached_distinct, 0,
                "RT._h5_coord_cache.crew_sig must stay observable after a "
                "stabilized update")
            self.assertLessEqual(
                cached_distinct, 2,
                "the cache-exposed crew signature must also come from at most "
                f"two distinct tables, but {cached_distinct} were observed")

    def test_stabilized_updates_keep_group_target_tables_stable(self):
        """Known positive: held groups keep the same ``state.targets`` table.

        This is a characterization, not a RED discriminant: the stable
        ``_h5_acquire_group`` path keeps the previously stored targets table
        while the freshly collected table is discarded. After the optimization
        the same observable must remain true.
        """
        lua = _local_runtime()
        _prepare(self, lua)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            _T = _T + 0.5
            RT:update(mgr, _T, .1)

            _saved_targets = {}
            _saved_keys = {}
            for key, state in pairs(RT._h5_groups or {}) do
                local relevant = (key == "local_p_p") or (key == "local_p_w")
                    or (key:sub(1, 5) == "crew_")
                if relevant and not state._release_pending then
                    _saved_keys[#_saved_keys + 1] = key
                    _saved_targets[key] = state.targets
                end
            end

            _T = _T + 0.5
            RT:update(mgr, _T, .1)

            _targets_stable = true
            _targets_missing = ""
            _targets_checked = 0
            for _, key in ipairs(_saved_keys) do
                local state = RT._h5_groups and RT._h5_groups[key]
                _targets_checked = _targets_checked + 1
                if not state or state._release_pending then
                    _targets_stable = false
                    _targets_missing = _targets_missing .. key .. ":released;"
                elseif state.targets ~= _saved_targets[key] then
                    _targets_stable = false
                    _targets_missing = _targets_missing .. key .. ":retargeted;"
                end
            end
        ''')
        g = lua.globals()
        self.assertGreaterEqual(int(g._targets_checked), 3,
                                "local_p_p, local_p_w and a crew group must be assessed")
        self.assertIs(g._targets_stable, True,
                      "held group target tables must stay stable across two "
                      f"stabilized updates: {g._targets_missing}")

    def test_frame_revalidation_calls_acquire_for_every_held_group(self):
        """Guard A: each held group revalidates through ``NV:acquire`` every frame.

        For two consecutive stabilized updates the wrapper records the real
        ``nv:acquire(owner, generation, requests)`` calls. Every held
        ``local_p_p``/``local_p_w``/``crew_*`` group must appear with its own
        owner, current generation and stored requests table, even when no
        source changed.
        """
        lua = _local_runtime()
        _prepare(self, lua)

        lua.execute(INSTALL_WORK_COUNTERS)
        results = []
        for _ in range(2):
            lua.execute(r'''
                local RT = kyohud.hud.runtime
                local mgr = managers.hud
                _reset_work_counters()
                _T = _T + 0.5
                RT:update(mgr, _T, .1)
                _check_held_acquire()
            ''')
            g = lua.globals()
            results.append((bool(g._acquire_ok), int(g._acquire_checked),
                            str(g._acquire_missing)))
        lua.execute("_restore_work_counters()")

        for index, (ok, checked, missing) in enumerate(results, start=1):
            self.assertGreaterEqual(
                checked, 3,
                f"update {index}: local_p_p, local_p_w and a crew group must be "
                "revalidated")
            self.assertIs(
                ok, True,
                f"update {index}: every held group must revalidate through "
                f"NV:acquire with its owner/generation/requests: {missing}")

    def test_dead_entry_panel_fails_closed_and_reacquires_same_primitives(self):
        """Guard B: a dead held entry panel releases the group, then recovers.

        The real fixture aliveness flag (``_alive``, read by ``alive``) marks
        the local entry panel dead. The next real update cannot collect local
        targets, so ``local_p_p`` is released and the native alpha values are
        restored. Restoring the panel lets a later update re-collect and
        re-acquire exactly the same leaf objects.
        """
        lua = _local_runtime()
        _prepare(self, lua)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            _dead_before_name = _LOCAL_NAME:alpha()
            _dead_saved_targets = {}
            for i, leaf in ipairs(RT._h5_groups["local_p_p"].targets) do
                _dead_saved_targets[i] = leaf
            end
            _dead_entry = _LOCAL

            _LOCAL._alive = false
            _T = _T + 0.5
            RT:update(mgr, _T, .1)

            _dead_group = RT._h5_groups and RT._h5_groups["local_p_p"] or nil
            _dead_released = (_dead_group == nil) or (_dead_group._release_pending == true)
            _dead_name_restored = _LOCAL_NAME:alpha() == .7
            _dead_radial_restored = _LOCAL_RADIAL_BG:alpha() == .7
                and _LOCAL_RADIAL_HEALTH:alpha() == .7
                and _LOCAL_RADIAL_SHIELD:alpha() == .7
            _dead_revive_restored = _LOCAL_REVIVE_BG:alpha() == .7

            _LOCAL._alive = true
            _T = _T + 0.5
            RT:update(mgr, _T, .1)

            local recovered = RT._h5_groups and RT._h5_groups["local_p_p"] or nil
            _dead_back = recovered ~= nil and recovered._release_pending ~= true
            _dead_same = recovered ~= nil
                and _same_leaf_set(recovered.targets, _dead_saved_targets)
            _dead_masked = _LOCAL_NAME:alpha() == 0
                and _LOCAL_RADIAL_BG:alpha() == 0
                and _LOCAL_RADIAL_HEALTH:alpha() == 0
                and _LOCAL_RADIAL_SHIELD:alpha() == 0
                and _LOCAL_REVIVE_BG:alpha() == 0
            _dead_entry_same = _LOCAL == _dead_entry
        ''')
        g = lua.globals()
        self.assertEqual(float(g._dead_before_name), 0.0,
                         "positive baseline: local_p_p must already mask name alpha")
        self.assertIs(g._dead_released, True,
                      "a dead held entry panel must release local_p_p")
        self.assertIs(g._dead_name_restored, True,
                      "releasing local_p_p must restore the native name alpha")
        self.assertIs(g._dead_radial_restored, True,
                      "releasing local_p_p must restore the native radial alphas")
        self.assertIs(g._dead_revive_restored, True,
                      "releasing local_p_p must restore the native revive alpha")
        self.assertIs(g._dead_back, True,
                      "restoring the entry panel must re-acquire local_p_p")
        self.assertIs(g._dead_entry_same, True,
                      "recovery must reuse the same entry panel object")
        self.assertIs(g._dead_same, True,
                      "recovery must reuse the exact same native leaf primitives")
        self.assertIs(g._dead_masked, True,
                      "re-acquired native leaves must be masked to alpha 0 again")

    def test_weapon_publication_recollects_weapon_targets(self):
        """Guard C: a real ammo publication invalidates the weapon collection.

        The equipped weapon base real setter ``_native_set_ammo`` changes the
        authoritative ammo, and the genuine ``weapons:refresh`` poll in the next
        update consumes it. The coordinator must pass a freshly collected
        ``local_p_w`` target table (not a cached one), keep the group held and
        reuse the same native leaves.
        """
        lua = _local_runtime()
        _prepare(self, lua)

        lua.execute(INSTALL_COORDINATE_OBSERVER)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud

            _co_reset()
            _T = _T + 0.5
            RT:update(mgr, _T, .1)
            _c_before_targets = _co.w_targets
            _c_before_calls = _co.w_calls
            _c_before_group = RT._h5_groups and RT._h5_groups["local_p_w"] or nil

            _co_reset()
            local base = inventory:equipped_unit():base()
            base:_native_set_ammo(30, 10, 120, 150)
            _T = _T + 0.5
            RT:update(mgr, _T, .1)
            _c_after_targets = _co.w_targets
            _c_after_calls = _co.w_calls
            _c_after_group = RT._h5_groups and RT._h5_groups["local_p_w"] or nil

            _c_clip = W._current_snapshot and W._current_snapshot.slots
                and W._current_snapshot.slots[2]
                and W._current_snapshot.slots[2].current_clip or nil
            _c_held = _c_after_group ~= nil
                and _c_after_group._release_pending ~= true
            _c_fresh = _c_before_targets ~= nil and _c_after_targets ~= nil
                and _c_before_targets ~= _c_after_targets
            _c_calls = _c_before_calls >= 1 and _c_after_calls >= 1
            _c_same_leaves = _same_leaf_set(_c_before_targets, _c_after_targets)
            _co_restore()
        ''')
        g = lua.globals()
        self.assertGreaterEqual(int(g._c_before_calls), 1,
                                "the stable update must collect local_p_w targets")
        self.assertGreaterEqual(int(g._c_after_calls), 1,
                                "the post-publication update must collect local_p_w targets")
        self.assertEqual(float(g._c_clip), 10.0,
                         "the genuine weapons refresh must consume the real "
                         "ammo setter (equipped slot 2 current_clip == 10)")
        self.assertIs(g._c_held, True,
                      "local_p_w must stay held across the weapon publication")
        self.assertIs(g._c_fresh, True,
                      "a weapon publication must force a fresh local_p_w target "
                      "collection instead of reusing the cached table")
        self.assertIs(g._c_same_leaves, True,
                      "the fresh weapon collection must reuse the same native leaves")

    def test_hidden_owned_root_releases_and_reacquires_local_group(self):
        """Guard D: hiding the owned root releases local_p_p, showing it recovers.

        The player updater is throttled through its real ``_last_update_time``
        field on the hide frame, which is a legitimate recovery frame shape
        (0.5 s recovery pass, 0.05 s player throttle). Hiding ``P._root`` then
        releases ``local_p_p`` and restores the native alphas. Showing the root
        lets a later update re-acquire the same primitives.
        """
        lua = _local_runtime()
        _prepare(self, lua)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud

            _root_saved_targets = {}
            for i, leaf in ipairs(RT._h5_groups["local_p_p"].targets) do
                _root_saved_targets[i] = leaf
            end
            _root_label = P._h5_id_label

            _T = _T + 0.5
            P._last_update_time = _T
            P._root:set_visible(false)
            RT:update(mgr, _T, .1)

            _root_hidden = P._root:visible() == false
            _root_group = RT._h5_groups and RT._h5_groups["local_p_p"] or nil
            _root_released = (_root_group == nil) or (_root_group._release_pending == true)
            _root_name_restored = _LOCAL_NAME:alpha() == .7
            _root_radial_restored = _LOCAL_RADIAL_BG:alpha() == .7
                and _LOCAL_RADIAL_HEALTH:alpha() == .7
                and _LOCAL_RADIAL_SHIELD:alpha() == .7

            P._root:set_visible(true)
            _T = _T + 0.5
            RT:update(mgr, _T, .1)

            local recovered = RT._h5_groups and RT._h5_groups["local_p_p"] or nil
            _root_back = recovered ~= nil and recovered._release_pending ~= true
            _root_same = recovered ~= nil
                and _same_leaf_set(recovered.targets, _root_saved_targets)
            _root_masked = _LOCAL_NAME:alpha() == 0
                and _LOCAL_RADIAL_BG:alpha() == 0
                and _LOCAL_RADIAL_HEALTH:alpha() == 0
                and _LOCAL_RADIAL_SHIELD:alpha() == 0
            _root_visible_back = P._root:visible() == true
            _root_label_same = P._h5_id_label == _root_label
        ''')
        g = lua.globals()
        self.assertIs(g._root_hidden, True,
                      "the throttled player updater must not repair the hidden root")
        self.assertIs(g._root_released, True,
                      "a hidden owned root must release local_p_p")
        self.assertIs(g._root_name_restored, True,
                      "releasing local_p_p must restore the native name alpha")
        self.assertIs(g._root_radial_restored, True,
                      "releasing local_p_p must restore the native radial alphas")
        self.assertIs(g._root_visible_back, True,
                      "the recovered owned root must be visible")
        self.assertIs(g._root_back, True,
                      "showing the root must re-acquire local_p_p")
        self.assertIs(g._root_same, True,
                      "recovery must reuse the exact same native leaf primitives")
        self.assertIs(g._root_masked, True,
                      "recovered native leaves must be masked to alpha 0 again")
        self.assertIs(g._root_label_same, True,
                      "recovery must reuse the same certified identity label")


if __name__ == "__main__":
    unittest.main()
