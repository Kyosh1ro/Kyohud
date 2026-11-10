"""Verify quality split: same-pass module certification vs throttled light check.

Contract (approved 2026-11-10, quality split):
- Each P/W/E/C update pass records `_update_ran_now` (main block executed, not a
  throttle early return) and `_verify_ok_now` (full verifier result for that
  pass). Tests executing the real modules directly must observe both fields.
- H5 consumes `_verify_ok_now` when `_update_ran_now` is true in the same pass.
  A throttled frame performs a real light root read (alive + visible + finite
  alpha > 0, plus the first expected crew card root) and never calls the full
  verifier.
- Certification decisions feed `_module_verified`/`_backdrop_coverage` without
  changing shared-backdrop coverage semantics.
- Corruption between meta frames is caught by the next meta frame (<= 0.05 s).

These tests execute the production chunks through the existing real-runtime
fixtures. No Python copy of the Lua logic is used.
"""
import unittest

from test_hud_e_native_replacement import _radial_runtime


def _bind_names(lua):
    lua.execute(r'''
        P = kyohud.hud.player
        W = kyohud.hud.weapons
        E = kyohud.hud.equipment
        C = kyohud.hud.crew
        RT = kyohud.hud.runtime
    ''')


def _instrument_all(lua, assertion_prefix=""):
    lua.execute(r'''
        local P = kyohud.hud.player
        local W = kyohud.hud.weapons
        local E = kyohud.hud.equipment
        local C = kyohud.hud.crew
        again_counts = {p = 0, w = 0, e = 0, c = 0}
        again_originals = {
            p = P.verify, w = W.verify, e = E.verify, c = C._verify_render,
        }
        P.verify = function(self, ...)
            again_counts.p = again_counts.p + 1
            return again_originals.p(self, ...)
        end
        W.verify = function(self, ...)
            again_counts.w = again_counts.w + 1
            return again_originals.w(self, ...)
        end
        E.verify = function(self, ...)
            again_counts.e = again_counts.e + 1
            return again_originals.e(self, ...)
        end
        C._verify_render = function(self, ...)
            again_counts.c = again_counts.c + 1
            return again_originals.c(self, ...)
        end
        again_reads = {p = 0, w = 0, e = 0, c = 0}
        local function spy_root(root, key)
            local visible, alpha = root.visible, root.alpha
            root.visible = function(self, ...)
                again_reads[key] = again_reads[key] + 1
                return visible(self, ...)
            end
            root.alpha = function(self, ...)
                again_reads[key] = again_reads[key] + 1
                return alpha(self, ...)
            end
        end
        spy_root(P._root, "p")
        spy_root(W._root, "w")
        spy_root(E._root, "e")
        spy_root(C._root, "c")
    ''')


class VerifyQualitySplitTests(unittest.TestCase):
    def test_direct_module_update_exposes_ran_and_verified_fields(self):
        lua = _radial_runtime()
        _bind_names(lua)
        lua.execute(r'''
            P:update(m, 2.0, .05)
            W:update(m, 2.0, .05)
            E:update(m, 2.0, .05)
            C:update(m, 2.0, .05)
            direct_meta = {
                p = P._update_ran_now, w = W._update_ran_now,
                e = E._update_ran_now, c = C._update_ran_now,
                pv = P._verify_ok_now, wv = W._verify_ok_now,
                ev = E._verify_ok_now, cv = C._verify_ok_now,
            }
            P:update(m, 2.01, .01)
            W:update(m, 2.01, .01)
            E:update(m, 2.01, .01)
            C:update(m, 2.01, .01)
            direct_throttled = {
                p = P._update_ran_now, w = W._update_ran_now,
                e = E._update_ran_now, c = C._update_ran_now,
            }
        ''')
        g = lua.globals()
        for name in ("p", "w", "e", "c", "pv", "wv", "ev", "cv"):
            self.assertTrue(bool(g.direct_meta[name]),
                            "direct meta updates must expose ran and verified")
        for name in ("p", "w", "e", "c"):
            self.assertFalse(bool(g.direct_throttled[name]),
                             "direct throttled updates must clear update_ran_now")

    def test_throttled_frame_uses_light_check_without_full_verify(self):
        lua = _radial_runtime()
        _bind_names(lua)
        _instrument_all(lua)
        lua.execute(r'''
            R:update(m, 1.61, .01)
            throttled_fields = {
                p = P._update_ran_now, w = W._update_ran_now,
                e = E._update_ran_now, c = C._update_ran_now,
            }
            throttled_verify = {
                p = again_counts.p, w = again_counts.w,
                e = again_counts.e, c = again_counts.c,
            }
            throttled_reads = {
                p = again_reads.p, w = again_reads.w,
                e = again_reads.e, c = again_reads.c,
            }
        ''')
        g = lua.globals()
        for name in ("p", "w", "e", "c"):
            self.assertFalse(bool(g.throttled_fields[name]))
        for name in ("p", "w", "e", "c"):
            self.assertEqual(
                g.throttled_verify[name], 0,
                "a throttled frame must not run the full verifier for %s" % name)
            self.assertGreater(
                g.throttled_reads[name], 0,
                "a throttled frame must actually read the %s root" % name)

    def test_meta_frame_consumes_module_certification_without_h5_reverify(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local P = kyohud.hud.player
            local W = kyohud.hud.weapons
            local E = kyohud.hud.equipment
            local C = kyohud.hud.crew
            again_counts = {p = 0, w = 0, e = 0, c = 0}
            again_originals = {
                update_p = P.update, update_w = W.update,
                update_e = E.update, update_c = C.update,
                verify_p = P.verify, verify_w = W.verify,
                verify_e = E.verify, verify_c = C._verify_render,
            }
            again_module = {p = 0, w = 0, e = 0, c = 0}
            P.verify = function(self, ...)
                again_counts.p = again_counts.p + 1
                return again_originals.verify_p(self, ...)
            end
            W.verify = function(self, ...)
                again_counts.w = again_counts.w + 1
                return again_originals.verify_w(self, ...)
            end
            E.verify = function(self, ...)
                again_counts.e = again_counts.e + 1
                return again_originals.verify_e(self, ...)
            end
            C._verify_render = function(self, ...)
                again_counts.c = again_counts.c + 1
                return again_originals.verify_c(self, ...)
            end
            local function timed(key, fn)
                return function(self, ...)
                    local before = again_counts[key]
                    local result = fn(self, ...)
                    again_module[key] = again_counts[key] - before
                    return result
                end
            end
            P.update = timed("p", again_originals.update_p)
            W.update = timed("w", again_originals.update_w)
            E.update = timed("e", again_originals.update_e)
            C.update = timed("c", again_originals.update_c)
            R:update(m, 1.7, .05)
            again_extra = {
                p = again_counts.p - again_module.p,
                w = again_counts.w - again_module.w,
                e = again_counts.e - again_module.e,
                c = again_counts.c - again_module.c,
            }
            again_ran = {
                p = P._update_ran_now, w = W._update_ran_now,
                e = E._update_ran_now, c = C._update_ran_now,
            }
            again_ok = {
                p = P._verify_ok_now, w = W._verify_ok_now,
                e = E._verify_ok_now, c = C._verify_ok_now,
            }
        ''')
        g = lua.globals()
        self.assertEqual(g.again_module.w, 1,
                         "weapons must certify exactly once in its meta pass")
        self.assertEqual(g.again_module.e, 1,
                         "equipment must certify exactly once in its meta pass")
        self.assertEqual(g.again_module.c, 1,
                         "crew must certify exactly once in its meta pass")
        for name in ("p", "w", "e", "c"):
            self.assertEqual(
                g.again_extra[name], 0,
                "H5 must not add a second verify call for %s" % name)
        for name in ("p", "w", "e", "c"):
            self.assertTrue(bool(g.again_ran[name]),
                            "a meta frame must report update_ran_now")
            self.assertTrue(bool(g.again_ok[name]),
                            "a meta frame must report verify_ok_now")

    def test_throttled_hidden_root_fails_closed_without_full_verify(self):
        cases = (
            ("invisible", "P._root:set_visible(false)"),
            ("alpha_zero", "P._root:set_alpha(0)"),
            ("dead", "P._root._alive = false; P.update = function() end"),
        )
        for name, corruption in cases:
            with self.subTest(name=name):
                lua = _radial_runtime()
                _bind_names(lua)
                _instrument_all(lua)
                lua.execute(corruption + '; R:update(m, 1.61, .01)')
                lua.execute(r'''
                    again_released = R._h5_groups == nil
                        or R._h5_groups["local_p_p"] == nil
                    again_restored = h:alpha()
                    again_ran = P._update_ran_now
                    again_verify_p = again_counts.p
                ''')
                g = lua.globals()
                self.assertTrue(bool(g.again_released),
                                "a failed light check must release local_p_p")
                self.assertAlmostEqual(float(g.again_restored), .7, places=2,
                                       msg="a failed light check must restore native")
                self.assertFalse(bool(g.again_ran))
                self.assertEqual(g.again_verify_p, 0,
                                 "the light check must not call the full verifier")

    def test_primitive_corruption_after_light_frame_is_repaired_on_meta_frame(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local P = kyohud.hud.player
            again_counts = {p = 0}
            local real_verify = P.verify
            P.verify = function(self, ...)
                again_counts.p = again_counts.p + 1
                return real_verify(self, ...)
            end
            local downs = P._downs_text
            local expected = P._exp_downs_text
            R:update(m, 1.61, .01)
            again_light_verify = again_counts.p
            local light_ran = P._update_ran_now
            downs:set_text("CORRUPT")
            R:update(m, 1.62, .01)
            again_second_light_verify = again_counts.p
            again_light_text = downs:text()
            again_light_verified = P._render_verified
            R:update(m, 1.7, .05)
            again_meta_verify = again_counts.p
            again_repaired = downs:text() == expected
            again_meta_ran = P._update_ran_now
            again_meta_ok = P._verify_ok_now
            again_group = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
        ''')
        g = lua.globals()
        self.assertEqual(g.again_light_verify, 0,
                         "the first throttled frame must only light-check")
        self.assertFalse(bool(g.light_ran))
        self.assertEqual(g.again_second_light_verify, 0,
                         "a second throttled frame must not detect the corruption")
        self.assertEqual(g.again_light_text, "CORRUPT",
                         "the approved compromise leaves corruption until the meta frame")
        self.assertTrue(bool(g.again_light_verified),
                        "the light check keeps the previous certified decision")
        self.assertGreater(g.again_meta_verify, 0,
                           "the next meta frame must run the full verifier")
        self.assertTrue(bool(g.again_repaired),
                        "the meta frame must repair the corrupted primitive")
        self.assertTrue(bool(g.again_meta_ran))
        self.assertTrue(bool(g.again_meta_ok))
        self.assertTrue(bool(g.again_group),
                        "the repaired local group stays acquired")

    def test_acquisition_surface_matches_across_meta_and_light_frames(self):
        lua = _radial_runtime()
        _bind_names(lua)
        lua.execute(r'''
            local function snapshot()
                local counts = {}
                for key, state in pairs(R._h5_groups or {}) do
                    counts[key] = #state.targets
                end
                return counts
            end
            R:update(m, 1.7, .05)
            again_meta_groups = snapshot()
            again_meta_masks = {
                h:alpha(), n:alpha(),
                kyohud.hud.player._root:visible(),
                kyohud.hud.crew._root:visible(),
            }
            R:update(m, 1.72, .01)
            again_light_groups = snapshot()
            again_light_masks = {
                h:alpha(), n:alpha(),
                kyohud.hud.player._root:visible(),
                kyohud.hud.crew._root:visible(),
            }
            again_parity = true
            for key, count in pairs(again_meta_groups) do
                if again_light_groups[key] ~= count then again_parity = false end
            end
            for key in pairs(again_light_groups) do
                if again_meta_groups[key] == nil then again_parity = false end
            end
            again_mask_parity = true
            for i = 1, #again_meta_masks do
                if again_meta_masks[i] ~= again_light_masks[i] then
                    again_mask_parity = false
                end
            end
        ''')
        g = lua.globals()
        self.assertTrue(bool(g.again_parity),
                        "light and meta frames must acquire the same groups/targets")
        self.assertTrue(bool(g.again_mask_parity),
                        "meta and light frames must keep the same masking")

    def test_skipped_module_update_is_treated_as_non_ran(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local P = kyohud.hud.player
            again_counts = {p = 0}
            local real_verify = P.verify
            P.verify = function(self, ...)
                again_counts.p = again_counts.p + 1
                return real_verify(self, ...)
            end
            local real_update = P.update
            P.update = function() end
            P._update_ran_now = true
            P._verify_ok_now = true
            R:update(m, 1.61, .01)
            again_non_ran = P._update_ran_now
            again_light_verify = again_counts.p
            again_group = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            P.update = real_update
            R:update(m, 1.7, .05)
            again_ran_again = P._update_ran_now == true
                and P._verify_ok_now == true
            again_meta_verify = again_counts.p
        ''')
        g = lua.globals()
        self.assertFalse(bool(g.again_non_ran),
                         "a module whose update did not run must not stay marked ran")
        self.assertEqual(g.again_light_verify, 0,
                         "the light check must cover a skipped module update")
        self.assertTrue(bool(g.again_group),
                        "the retained rendered group must survive a skipped update")
        self.assertTrue(bool(g.again_ran_again),
                        "the next meta pass must restore the ran/verified fields")
        self.assertGreater(g.again_meta_verify, 0,
                           "the next meta pass must run the full verifier")


if __name__ == "__main__":
    unittest.main()
