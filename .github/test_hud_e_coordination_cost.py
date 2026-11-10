"""Native-coordination call budgets, not Diesel timings or FPS claims."""
import unittest

from test_hud_e_native_replacement import _radial_runtime
from test_hud_native_visibility import _lua_with


_SEED_CREW_NATIVE = r'''
    local ACT = kyohud.hud.actors
    crew_slot, crew_pos = nil, nil
    for _, e in ipairs(ACT:get_crew_snapshot()) do
        if e.name and e.position and e.slot then
            crew_slot, crew_pos = e.slot, e.position
            break
        end
    end
    assert(crew_slot and crew_pos, "fixture must expose an occupied named crew slot")
    local crew_entry = m._teammate_panels[crew_slot]
    assert(type(crew_entry) == "table", "native crew slot entry must exist")
    crew_ep = panel_double:panel({name = "teammate_" .. crew_slot})
    crew_ep:set_shape(0, 0, 280, 120)
    crew_ep:set_visible(true)
    n_crew = crew_ep:text({name = "name", text = "NativeCrew"})
    n_crew:set_shape(10, 0, 80, 20)
    n_crew:set_visible(true)
    n_crew:set_alpha(.7)
    crew_entry._panel = crew_ep
    R._last_recovery_time = 1.99
'''


class CoordinationCostTests(unittest.TestCase):
    def test_stable_generation_keeps_registry_but_detects_same_length_replacement(self):
        lua, loaded = _lua_with(None)
        self.assertTrue(loaded)
        lua.execute('''
            local o = _make_obj("stable")
            local svc = kyohud.hud.native_visibility:new({[o] = {alpha = true}})
            local request = {{id = o, property = "alpha", value = 0}}
            assert(svc:acquire("one", 1, request))
            local registry = svc._entries
            assert(svc:acquire("one", 1, request))
            registry_retained = rawequal(registry, svc._entries)
            -- Deliberately replace a private record without changing its count.
            -- A cached binding must not authorize against the orphaned record.
            svc._entries[1] = {
                object = o, property = "alpha", old_value = 1,
                applied_value = 0, owner = "other", generation = 1,
            }
            replacement_accepted = svc:acquire("one", 1, request)
        ''')
        self.assertTrue(lua.globals().registry_retained,
                        "same generation must not rebuild its unchanged registry")
        self.assertFalse(lua.globals().replacement_accepted)

    def test_native_userdata_aliases_still_conflict_as_the_same_object(self):
        lua, loaded = _lua_with(None)
        self.assertTrue(loaded)
        lua.execute('''
            local state = {alpha = .7}
            local first = newproxy(true)
            local alias = newproxy(first)
            local mt = getmetatable(first)
            mt.__eq = function() return true end
            mt.__index = {
                _alive = true,
                alpha = function() return state.alpha end,
                set_alpha = function(_, value) state.alpha = value end,
            }
            assert(first == alias and not rawequal(first, alias))
            local svc = kyohud.hud.native_visibility:new({
                [first] = {alpha = true}, [alias] = {alpha = true},
            })
            assert(svc:acquire("one", 1, {{id = first, property = "alpha", value = 0}}))
            alias_conflict = svc:acquire("other", 1, {{id = alias, property = "alpha", value = 0}})
            for i = 1, 32 do
                local next_alias = newproxy(first)
                svc._whitelist[next_alias] = {alpha = true}
                assert(svc:acquire("one", 1, {{id = next_alias, property = "alpha", value = 0}}))
            end
            cached_alias_keys = 0
            for _ in pairs(svc._entry_index.alpha) do cached_alias_keys = cached_alias_keys + 1 end
        ''')
        self.assertFalse(lua.globals().alias_conflict,
                         "raw hash identity must not weaken native __eq ownership")
        self.assertEqual(lua.globals().cached_alias_keys, 1,
                         "the index must not accumulate fresh wrappers for one native object")

    def test_identity_updates_and_corruption_still_repair_the_same_label(self):
        lua = _radial_runtime()
        lua.execute('''
            saved_identity = kyohud.hud.player._h5_id_label
            n:set_text("Changed peer name")
            n:set_color(Color(1, .25, .5, .75))
            n:set_alpha(0)
            R:_coordinate_h5_native_duplicates()
        ''')
        self.assertEqual(lua.eval("saved_identity:text()"), "Changed peer name")
        lua.execute('''
            saved_identity:set_shape(-100, -100, 1, 1)
            saved_identity:set_color(Color(1, .1, .1, .1))
            saved_identity:set_alpha(.2)
            saved_identity:set_visible(false)
            R:_coordinate_h5_native_duplicates()
        ''')
        self.assertTrue(lua.eval("kyohud.hud.player._h5_id_label == saved_identity"))
        self.assertTrue(lua.eval("saved_identity:visible()"))
        self.assertEqual(lua.eval("saved_identity:alpha()"), 1)
        self.assertAlmostEqual(lua.eval("saved_identity:color().r"), .25)
        self.assertAlmostEqual(lua.eval("saved_identity:color().g"), .5)
        self.assertAlmostEqual(lua.eval("saved_identity:color().b"), .75)
        self.assertTrue(lua.eval("math.abs(saved_identity:x() - 14 * kyohud.hud.player._root:w() / 380) < .01"))
        self.assertEqual(lua.eval("h:alpha()"), 0)

    def test_failed_identity_repair_restores_native_name_then_recovers(self):
        lua = _radial_runtime()
        lua.execute('''
            saved_identity = kyohud.hud.player._h5_id_label
            saved_identity:set_shape(-100, -100, 1, 1)
            saved_identity_shape = saved_identity.set_shape
            saved_identity.set_shape = function() end
            R:_coordinate_h5_native_duplicates()
        ''')
        self.assertEqual(lua.eval("n:alpha()"), .7)
        self.assertEqual(lua.eval("h:alpha()"), 0,
                         "a name failure must not discard the still-certified gauge")
        self.assertFalse(lua.eval("saved_identity:visible()"))
        lua.execute('''
            saved_identity.set_shape = saved_identity_shape
            R:_coordinate_h5_native_duplicates()
        ''')
        self.assertEqual(lua.eval("h:alpha()"), 0)
        self.assertTrue(lua.eval("saved_identity:visible()"))
        self.assertTrue(lua.eval("kyohud.hud.player._h5_id_label == saved_identity"))

    def test_indexed_batch_preserves_duplicates_both_properties_and_generation_restore(self):
        lua, loaded = _lua_with(None)
        self.assertTrue(loaded)
        lua.execute('''
            o = _make_obj("both")
            svc = kyohud.hud.native_visibility:new({[o] = {alpha = true, visible = true}})
            local requests = {
                {id = o, property = "alpha", value = 0},
                {id = o, property = "alpha", value = 0},
                {id = o, property = "visible", value = false},
                {id = o, property = "visible", value = false},
            }
            assert(svc:acquire("owner", 1, requests))
            assert(#svc._entries == 2 and o:alpha() == 0 and o:visible() == false)
            assert(not svc:acquire("other", 1, requests))
            requests[1].value, requests[2].value = .25, .25
            assert(svc:acquire("owner", 2, requests))
            assert(#svc._entries == 2 and o:alpha() == .25 and o:visible() == false)
            svc:release("owner", 2)
            assert(#svc._entries == 0 and o:alpha() == 1 and o:visible() == true)
            assert(svc._entry_index == nil and svc._indexed_entries == nil)
        ''')

    def test_stable_local_identity_does_not_dirty_its_primitives_each_frame(self):
        lua = _radial_runtime()
        lua.execute('''
            identity_writes = {}
            identity_label = kyohud.hud.player._h5_id_label
            for _, name in ipairs({"set_visible", "set_alpha", "set_color", "set_shape"}) do
                local method = identity_label[name]
                identity_label[name] = function(self, ...)
                    identity_writes[name] = (identity_writes[name] or 0) + 1
                    return method(self, ...)
                end
            end
            for i = 1, 5 do R:_coordinate_h5_native_duplicates() end
        ''')
        self.assertEqual(dict(lua.globals().identity_writes.items()), {},
                         "an unchanged identity needs no visibility/style/shape setters")
        self.assertEqual(lua.eval("h:alpha()"), 0)
        self.assertTrue(lua.eval("kyohud.hud.player._h5_id_label == identity_label"))

    def test_stable_identity_reads_ink_and_geometry_exactly_once_per_pass(self):
        lua = _radial_runtime()
        lua.execute('''
            local P = kyohud.hud.player
            identity_label = P._h5_id_label
            assert(identity_label and P._h5_identity_verified == true,
                "fixture must start from a warmed certified identity")
            reads = {}
            for _, name in ipairs({"text_rect", "x", "y", "w", "h"}) do
                local method = identity_label[name]
                reads[name] = 0
                identity_label[name] = function(self, ...)
                    reads[name] = reads[name] + 1
                    return method(self, ...)
                end
            end
            identity_writes = {}
            for _, name in ipairs({"set_visible", "set_alpha", "set_color",
                "set_shape", "set_text", "set_font_size"}) do
                local method = identity_label[name]
                identity_label[name] = function(self, ...)
                    identity_writes[name] = (identity_writes[name] or 0) + 1
                    return method(self, ...)
                end
            end
            R:_coordinate_h5_native_duplicates()
            first_ink_reads = reads.text_rect
            first_x_reads, first_y_reads = reads.x, reads.y
            first_w_reads, first_h_reads = reads.w, reads.h
            R:_coordinate_h5_native_duplicates()
            second_ink_reads = reads.text_rect - first_ink_reads
            second_x_reads = reads.x - first_x_reads
            second_y_reads = reads.y - first_y_reads
            second_w_reads = reads.w - first_w_reads
            second_h_reads = reads.h - first_h_reads
            stable_verified = (P._h5_identity_verified == true)
            retained_identity = (P._h5_id_label == identity_label)
            stable_n_alpha = n:alpha()
            stable_h_alpha = h:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(g.first_ink_reads, 1,
                         "a warmed stable pass must measure label ink exactly once")
        self.assertEqual(g.first_x_reads, 1,
                         "a warmed stable pass must read label x() exactly once")
        self.assertEqual(g.first_y_reads, 1,
                         "a warmed stable pass must read label y() exactly once")
        self.assertEqual(g.first_w_reads, 1,
                         "a warmed stable pass must read label w() exactly once")
        self.assertEqual(g.first_h_reads, 1,
                         "a warmed stable pass must read label h() exactly once")
        self.assertGreaterEqual(g.second_ink_reads, 1,
                                "an independent pass must freshly re-measure ink")
        self.assertGreaterEqual(g.second_x_reads, 1,
                                "an independent pass must freshly re-read x()")
        self.assertGreaterEqual(g.second_y_reads, 1,
                                "an independent pass must freshly re-read y()")
        self.assertGreaterEqual(g.second_w_reads, 1,
                                "an independent pass must freshly re-read w()")
        self.assertGreaterEqual(g.second_h_reads, 1,
                                "an independent pass must freshly re-read h()")
        self.assertTrue(g.stable_verified,
                        "a bounded read budget must not break certification")
        self.assertTrue(g.retained_identity,
                        "the identity label must be retained, not rebuilt")
        self.assertEqual(g.stable_n_alpha, 0)
        self.assertEqual(g.stable_h_alpha, 0)
        self.assertEqual(dict(g.identity_writes.items()), {},
                         "an unchanged identity needs no label setters")

    def test_identity_boundary_ink_fits_target_width_but_exceeds_actual_width(self):
        lua = _radial_runtime()
        lua.execute('''
            local P = kyohud.hud.player
            local label = P._h5_id_label
            assert(label and P._h5_identity_verified == true,
                "boundary must start from a positive certified retained label")
            local root_w = P._root:w()
            local e = root_w / 380
            local target_x, target_y, target_w, target_h = 14 * e, 170 * e, 352 * e, 20 * e
            label:set_shape(target_x, target_y, target_w - 0.005, target_h)
            local real_text_rect = label.text_rect
            local _, _, real_ink_w, real_ink_h = label:text_rect()
            assert(real_ink_w <= target_w - 0.005,
                "real ink must already fit the shrunken actual width")
            label.text_rect = function(self)
                return 0, 0, target_w - 0.002, real_ink_h
            end
            R:_coordinate_h5_native_duplicates()
            boundary_identity = P._h5_identity_verified
            boundary_n_alpha = n:alpha()
            boundary_label_visible = label:visible()
            boundary_h_alpha = h:alpha()
            label.text_rect = real_text_rect
            label:set_shape(target_x, target_y, target_w, target_h)
            R:_coordinate_h5_native_duplicates()
            recovered_identity = (P._h5_identity_verified == true)
            same_label = (P._h5_id_label == label)
            recovered_label_visible = label:visible()
            recovered_n_alpha = n:alpha()
            recovered_h_alpha = h:alpha()
        ''')
        g = lua.globals()
        self.assertIs(g.boundary_identity, False,
                      "ink wider than the actual leaf must fail identity certification")
        self.assertEqual(g.boundary_n_alpha, .7,
                         "a failed identity must restore the native name leaf")
        self.assertFalse(g.boundary_label_visible,
                         "the uncertified identity label must be hidden")
        self.assertEqual(g.boundary_h_alpha, 0,
                         "the still-certified health mask must survive the identity failure")
        self.assertTrue(g.recovered_identity,
                        "restoring real ink and shape must recover certification")
        self.assertTrue(g.same_label,
                        "recovery must reuse the same retained label")
        self.assertTrue(g.recovered_label_visible)
        self.assertEqual(g.recovered_n_alpha, 0,
                         "recovery must re-mask the native name leaf")
        self.assertEqual(g.recovered_h_alpha, 0)

    def test_reaffirming_a_batch_does_not_rescan_the_registry_per_leaf(self):
        lua, loaded = _lua_with(None)
        self.assertTrue(loaded)
        lua.execute('''
            local whitelist, requests = {}, {}
            for i = 1, 64 do
                local o = _make_obj("leaf_" .. i)
                whitelist[o] = {alpha = true}
                requests[i] = {id = o, property = "alpha", value = 0}
            end
            svc = kyohud.hud.native_visibility:new(whitelist)
            assert(svc:acquire("stable", 1, requests))
            registry_reads = 0
            for _, entry in ipairs(svc._entries) do
                local object = entry.object
                entry.object = nil
                setmetatable(entry, {__index = function(_, key)
                    if key == "object" then
                        registry_reads = registry_reads + 1
                        return object
                    end
                end})
            end
            reaffirmed = svc:acquire("stable", 1, requests)
            stable_entries = #svc._entries
            for _, request in ipairs(requests) do assert(request.id:alpha() == 0) end
        ''')
        self.assertTrue(lua.globals().reaffirmed)
        self.assertEqual(lua.globals().stable_entries, 64)
        self.assertLessEqual(lua.globals().registry_reads, 128,
                             "at most two linear registry passes for a batch")

    def test_replacing_a_verifier_invalidates_the_same_pass_receipt(self):
        lua = _radial_runtime()
        lua.execute('''
            local certifications = R:_coordinate_h5_native_duplicates()
            local P = kyohud.hud.player
            local verify = P.verify
            replacement_checks = 0
            P.verify = function(self, ...)
                replacement_checks = replacement_checks + 1
                return verify(self, ...)
            end
            receipt_backdrop_valid = R:_verify_local_backdrop(certifications)
        ''')
        self.assertEqual(lua.globals().replacement_checks, 1)
        self.assertTrue(lua.globals().receipt_backdrop_valid)

    def test_h5_shares_only_read_only_root_ancestry_then_observes_failure(self):
        lua = _radial_runtime()
        lua.execute('''
            h5_parent_reads = 0
            local parent = R._parent_panel
            local visible = parent.visible
            parent.visible = function(self)
                h5_parent_reads = h5_parent_reads + 1
                if h5_parent_fault then error("unknown parent") end
                return visible(self)
            end
            R:_coordinate_h5_native_duplicates()
        ''')
        self.assertEqual(lua.globals().h5_parent_reads, 1)
        self.assertEqual(lua.eval("h:alpha()"), 0)
        lua.execute("h5_parent_fault = true; R:_coordinate_h5_native_duplicates()")
        self.assertEqual(lua.eval("h:alpha()"), 0.7)
        lua.execute("h5_parent_fault = false; R:_coordinate_h5_native_duplicates()")
        self.assertEqual(lua.eval("h:alpha()"), 0)

    def test_priority_reads_shared_ancestry_once_and_rechecks_next_pass(self):
        lua = _radial_runtime()
        lua.execute('''
            for _, name in ipairs({"radial_custom", "radial_ability", "radial_rip"}) do
                local leaf = rad:bitmap({name = name})
                leaf:set_shape(5, 5, 5, 5)
                leaf:set_visible(true)
            end
            priority_reads = 0
            local parent = R._parent_panel
            local visible = parent.visible
            parent.visible = function(self)
                priority_reads = priority_reads + 1
                if priority_fault then error("unknown visibility") end
                return visible(self)
            end
            R:_apply_native_priority()
        ''')
        self.assertEqual(lua.globals().priority_reads, 1)
        self.assertTrue(lua.eval("kyohud.hud.player._root:visible()"))
        lua.execute("priority_fault = true; priority_reads = 0; R:_apply_native_priority()")
        self.assertEqual(lua.globals().priority_reads, 1)
        self.assertFalse(lua.eval("kyohud.hud.player._root:visible()"),
                         "a new getter failure must not reuse a prior visible result")
        lua.execute("priority_fault = false; R:update(m, 10, .1)")
        self.assertTrue(lua.eval("kyohud.hud.player._root:visible()"))

    def test_local_certification_reused_inside_sync_but_not_between_images(self):
        # quality split approved 2026-11-10: H5 consumes the P/W/E result from
        # the same update pass instead of re-running the full verifier, and a
        # throttled frame only performs the approved light root check.
        lua = _radial_runtime()
        lua.execute('''
            certification_counts = {}
            for _, name in ipairs({"player", "weapons", "equipment"}) do
                local module = kyohud.hud[name]
                local verify = module.verify
                module.verify = function(self, ...)
                    certification_counts[name] = (certification_counts[name] or 0) + 1
                    return verify(self, ...)
                end
            end
            R:_sync_local_backdrop(10)
        ''')
        for name in ("player", "weapons", "equipment"):
            # The receipt is consumed, so verify was never called: the key may be absent.
            self.assertEqual(lua.globals().certification_counts[name] or 0, 0)
        self.assertTrue(lua.eval("R._local_backdrop_verified"))
        lua.execute('''
            local root = kyohud.hud.player._root
            local original_set_shape = root.set_shape
            root:set_shape(root:x() + 20, root:y(), root:w(), root:h())
            root.set_shape = function() end
            R:update(m, 1.61, .01)
            light_verify = (certification_counts["player"] or 0)
            light_alpha = h:alpha()
            R:update(m, 1.7, .05)
            meta_verify = certification_counts["player"]
            meta_alpha = h:alpha()
            root.set_shape = original_set_shape
            R:update(m, 1.8, .05)
            recovered_alpha = h:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(g.light_verify, 0,
                         "a throttled frame must not run the full verifier")
        self.assertEqual(g.light_alpha, 0,
                         "the approved compromise keeps masking until the meta frame")
        self.assertGreater(g.meta_verify, 0,
                           "the next meta frame must run the full verifier")
        self.assertEqual(g.meta_alpha, 0.7,
                         "a failed meta certification must restore native")
        self.assertEqual(g.recovered_alpha, 0,
                         "a repaired meta frame must re-suppress native")

    def test_h5_certifies_each_expected_crew_card_only_once(self):
        # quality split approved 2026-11-10: the meta crew pass certifies each
        # expected card once; H5 consumes that result instead of re-verifying.
        lua = _radial_runtime()
        lua.execute('''
            local C = kyohud.hud.crew
            card_checks = {}
            for i = 1, 3 do
                local card = C._cards[i]
                local verify = card.verify
                card.verify = function(self, ...)
                    card_checks[i] = (card_checks[i] or 0) + 1
                    return verify(self, ...)
                end
            end
            R:update(m, 1.7, .05)
        ''')
        self.assertTrue(lua.eval("kyohud.hud.crew._render_verified"))
        active = [i for i in range(1, 4)
                  if lua.eval(f"kyohud.hud.crew._expected_positions[{i}]")]
        self.assertGreater(len(active), 0)
        for i in range(1, 4):
            self.assertEqual(lua.globals().card_checks[i], 1 if i in active else None)

    def test_full_update_does_not_repeat_successful_crew_certification_within_one_invocation(self):
        lua = _radial_runtime()
        lua.execute(_SEED_CREW_NATIVE)
        lua.execute(r'''
            local C = kyohud.hud.crew
            verify_calls = 0
            local real_verify = C._verify_render
            C._verify_render = function(self, ...)
                verify_calls = verify_calls + 1
                return real_verify(self, ...)
            end
            R:update(m, 2.0, .05)
            first_frame_calls = verify_calls
            first_verified = (C._render_verified == true)
            first_native_alpha = n_crew:alpha()
            first_h_alpha, first_n_alpha = h:alpha(), n:alpha()
            R:update(m, 2.02, .05)
            second_frame_calls = verify_calls - first_frame_calls
            second_verified = (C._render_verified == true)
            second_native_alpha = n_crew:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(g.first_frame_calls, 1,
                         "a presentation-due RT:update must certify crew exactly once")
        self.assertTrue(bool(g.first_verified),
                        "the single certification must be positive")
        self.assertEqual(g.first_native_alpha, 0,
                         "the certified crew card must actually suppress its native leaf")
        self.assertEqual(g.first_h_alpha, 0)
        self.assertEqual(g.first_n_alpha, 0)
        self.assertEqual(g.second_frame_calls, 0,
                         "a sub-present-interval frame must use the light check, not a full certification")
        self.assertTrue(bool(g.second_verified),
                        "the light check must preserve the previous certified decision")
        self.assertEqual(g.second_native_alpha, 0)

    def test_retained_card_corruption_deferred_to_meta_frame_with_same_primitive_recovery(self):
        lua = _radial_runtime()
        lua.execute(_SEED_CREW_NATIVE)
        lua.execute(r'''
            local C = kyohud.hud.crew
            R:update(m, 2.0, .05)
            masked_alpha = n_crew:alpha()
            saved_card = C._cards[crew_pos]
            saved_root = saved_card.root
            saved_name = saved_card._name_text
            expected_name = saved_name:text()
            saved_name:set_text("CORRUPT")
            R:update(m, 2.02, .05)
            subthrottle_verified = (C._render_verified == true)
            subthrottle_alpha = n_crew:alpha()
            subthrottle_text = saved_name:text()
            kept_h_alpha, kept_n_alpha = h:alpha(), n:alpha()
            R:update(m, 2.12, .05)
            recovered_alpha = n_crew:alpha()
            recovered_verified = (C._render_verified == true)
            recovered_visible = saved_root:visible()
            repaired_name = saved_name:text()
            same_card = (saved_card == C._cards[crew_pos])
            same_root = (saved_root == saved_card.root)
            same_name = (saved_name == saved_card._name_text)
        ''')
        g = lua.globals()
        self.assertEqual(g.masked_alpha, 0,
                         "the first frame must suppress the native crew leaf")
        self.assertTrue(bool(g.subthrottle_verified),
                        "the sub-throttle light check keeps the prior certification")
        self.assertEqual(g.subthrottle_alpha, 0,
                         "the light check must keep masking a retained card")
        self.assertEqual(g.subthrottle_text, "CORRUPT",
                         "the approved compromise defers primitive repair to the meta frame")
        self.assertEqual(g.kept_h_alpha, 0,
                         "the local native health mask must survive the crew light check")
        self.assertEqual(g.kept_n_alpha, 0)
        self.assertEqual(g.recovered_alpha, 0,
                         "a meta update must keep the native crew leaves suppressed")
        self.assertTrue(bool(g.recovered_verified))
        self.assertTrue(bool(g.recovered_visible))
        self.assertEqual(g.repaired_name, g.expected_name,
                         "the retained name primitive must be repaired in place")
        self.assertTrue(bool(g.same_card))
        self.assertTrue(bool(g.same_root))
        self.assertTrue(bool(g.same_name))

    def test_native_condition_timer_over_crew_hides_crew_and_restores_leaf_on_receipt_frame(self):
        lua = _radial_runtime()
        lua.execute(_SEED_CREW_NATIVE)
        lua.execute(r'''
            local C = kyohud.hud.crew
            local t0, tA, tB = 2.0, 2.1, 2.2
            R:update(m, t0, .05)
            t0_verified = (C._render_verified == true)
            t0_alpha = n_crew:alpha()
            saved_card = C._cards[crew_pos]
            local ct = crew_ep:text({name = "condition_timer", text = "10"})
            ct:set_shape(C._root:x() + 10, C._root:y() + 10, 50, 20)
            ct:set_visible(true)
            R:update(m, tA, .05)
            receipt_frame_presented = (C._last_present_time == tA)
            crew_hidden = (not C._root:visible())
            timer_frame_alpha = n_crew:alpha()
            timer_h_alpha, timer_n_alpha = h:alpha(), n:alpha()
            player_root_visible = kyohud.hud.player._root:visible()
            ct:set_visible(false)
            R:update(m, tB, .05)
            cleared_alpha = n_crew:alpha()
            crew_visible = C._root:visible()
            recovered_verified = (C._render_verified == true)
            same_card = (saved_card == C._cards[crew_pos])
            card_visible = saved_card.root:visible()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g.t0_verified),
                        "the overlap scenario must start from a positive certification")
        self.assertEqual(g.t0_alpha, 0)
        self.assertTrue(bool(g.receipt_frame_presented),
                        "the overlapping frame must still be presentation-due and produce its receipt")
        self.assertTrue(bool(g.crew_hidden),
                        "an active native condition timer over the crew root must hide the crew")
        self.assertAlmostEqual(float(g.timer_frame_alpha), .7, places=2,
                               msg="the crew native ordinary name leaf must be restored on the receipt frame")
        self.assertEqual(g.timer_h_alpha, 0,
                         "the local native health mask must be untouched by the crew-only obstacle")
        self.assertEqual(g.timer_n_alpha, 0)
        self.assertTrue(bool(g.player_root_visible))
        self.assertEqual(g.cleared_alpha, 0,
                         "removing the obstacle must let a normal update re-suppress the crew leaf")
        self.assertTrue(bool(g.crew_visible))
        self.assertTrue(bool(g.recovered_verified))
        self.assertTrue(bool(g.same_card),
                        "the same card must be restored, not recreated")
        self.assertTrue(bool(g.card_visible))


if __name__ == "__main__":
    unittest.main()
