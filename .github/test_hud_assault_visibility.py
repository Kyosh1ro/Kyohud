"""LOT3a -- hud/assault.lua native visibility: one acquisition->disable transition (RED).

Scope: a single transition -- mount/update acquires 14 native targets via
kyohud.hud.native_visibility, then disable (enable_assault=false + refresh_settings)
restores every original value and clears all records.

Native structure (fixture via attach_native in test_hud_assault_render):
  _hud_panel (safe parent, visible=true)
    assault_panel (visible=false)
      icon_assaultbox (rect, visible=true, alpha=1)
      bg_box (unnamed panel, visible=true)
        bg, left_top, left_bottom, right_top (visible=true, alpha=0.37)
        right_bottom (visible=false, alpha=0.37) -- decorative
        text_panel (panel child of bg_box, alpha=0.37) -- the one alpha exception
      text_panel (panel child of assault_panel, visible=true) -- not targeted
      third_party (panel sibling under assault_panel, visible=true) -- not targeted
    hostages_panel (visible=true)
      hostages_icon (rect, visible=true, alpha=1)
      hostages_bg_box (named panel, visible=true)
        bg, left_top, left_bottom, right_top, right_bottom (visible=true, alpha=0.37)
        num_hostages (text child, visible=true, alpha=0.37)
    point_of_no_return_panel (visible=false) -- sentinel
    casing_panel (visible=false) -- sentinel
    buffs_panel (visible=false) -- sentinel
    (no wave_panel -- should_display_waves returns false)

Corner state: _point_of_no_return=false, _casing=false, _assault_mode="normal".

Expected 14 NV targets after acquisition:
  1 alpha target: text_panel (bg_box child) -> alpha 0
  13 visible targets:
    bg_box leaves: bg, left_top, left_bottom, right_top, right_bottom
    hostages_bg_box leaves: bg, left_top, left_bottom, right_top, right_bottom
    hostages_bg_box child: num_hostages
    icon_assaultbox
    hostages_icon

On disable: restore text_panel alpha to 0.37, all static leaves to original
(the decorative right_bottom stays false), NV entries cleared, owned root removed.

RED: production does not yet implement native acquisition for assault.
"""
from pathlib import Path
import unittest

from test_hud_assault_render import (
    _lua_with_assault_state,
    ASSAULT_PATH,
)


class AssaultNativeAcquireDisableTransitionTests(unittest.TestCase):
    """One real mount/update -> acquire 14 targets; disable -> restore all."""

    def test_mount_acquires_fourteen_targets_disable_restores(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            assert(RT._root_panel, "RT._root_panel must exist after mount")

            local A = kyohud.hud.assault
            assert(A, "A must exist")
            assert(type(A.mount) == "function",
                "RED: A:mount must be a function")

            A:mount(managers.hud)
            assert(A._root_panel,
                "RED: A._root_panel must exist after mount")

            A:update(managers.hud, 1.0, 0.05)

            local nv = kyohud.hud.native_visibility
            local nv_count = 0
            for _, e in ipairs(nv._entries or {}) do
                nv_count = nv_count + 1
            end
            assert(nv_count == 14,
                "RED: expected exactly 14 NV entries after acquire, got "
                .. tostring(nv_count))

            local tp_alpha = _na.text_panel:alpha()
            assert(math.abs(tp_alpha - 0) < 0.001,
                "RED: text_panel alpha must be 0 after acquire, got "
                .. tostring(tp_alpha))

            local static_leaves = {
                _na.bg_leaf, _na.left_top, _na.left_bottom,
                _na.right_top, _na.right_bottom,
                _na.h_bg, _na.h_lt, _na.h_lb, _na.h_rt, _na.h_rb,
                _na.num_hostages, _na.icon_assaultbox, _na.hostages_icon,
            }
            for i, leaf in ipairs(static_leaves) do
                local v = leaf:visible()
                assert(v == false,
                    "RED: static leaf #" .. i .. " must be visible=false, got "
                    .. tostring(v))
            end

            local alpha_entries = 0
            local visible_entries = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.property == "alpha" then
                    alpha_entries = alpha_entries + 1
                    assert(e.object == _na.text_panel,
                        "RED: only text_panel may have alpha entry")
                    assert(e.applied_value == 0,
                        "RED: text_panel applied alpha must be 0")
                    assert(math.abs(e.old_value - 0.37) < 0.01,
                        "RED: text_panel old alpha must be 0.37, got "
                        .. tostring(e.old_value))
                elseif e.property == "visible" then
                    visible_entries = visible_entries + 1
                    assert(e.applied_value == false,
                        "RED: visible entries must apply false")
                else
                    error("RED: unexpected property " .. tostring(e.property))
                end
            end
            assert(alpha_entries == 1,
                "RED: exactly 1 alpha entry, got " .. tostring(alpha_entries))
            assert(visible_entries == 13,
                "RED: exactly 13 visible entries, got " .. tostring(visible_entries))

            assert(_na.hud_panel:visible() == true,
                "RED: hud_panel must not be mutated")
            assert(_na.assault_panel:visible() == false,
                "RED: assault_panel initial visible=false must be preserved")
            assert(_na.hostages_panel:visible() == true,
                "RED: hostages_panel must not be mutated")
            assert(_na.bg_box:visible() == true,
                "RED: bg_box parent must not be mutated")
            assert(_na.hostages_bg_box:visible() == true,
                "RED: hostages_bg_box parent must not be mutated")
            assert(_na.third_party:visible() == true,
                "RED: third_party must not be mutated")
            assert(_na.ap_text_panel:visible() == true,
                "RED: assault_panel text_panel must not be mutated")
            assert(_na.pnr_panel:visible() == false,
                "RED: pnr sentinel must not be mutated")
            assert(_na.casing_panel:visible() == false,
                "RED: casing sentinel must not be mutated")
            assert(_na.buffs_panel:visible() == false,
                "RED: buffs sentinel must not be mutated")

            local corner = managers.hud._hud_assault_corner
            assert(corner._point_of_no_return == false,
                "RED: corner _point_of_no_return must not be mutated")
            assert(corner._casing == false,
                "RED: corner _casing must not be mutated")
            assert(corner._assault_mode == "normal",
                "RED: corner _assault_mode must not be mutated")

            kyohud.settings.enable_assault = false
            A:refresh_settings(managers.hud)

            local tp_alpha_after = _na.text_panel:alpha()
            assert(math.abs(tp_alpha_after - 0.37) < 0.01,
                "RED: text_panel alpha must restore to 0.37, got "
                .. tostring(tp_alpha_after))

            assert(_na.right_bottom:visible() == false,
                "RED: decorative leaf (originally false) must stay false")

            local restore_leaves = {
                _na.bg_leaf, _na.left_top, _na.left_bottom, _na.right_top,
                _na.h_bg, _na.h_lt, _na.h_lb, _na.h_rt, _na.h_rb,
                _na.num_hostages, _na.icon_assaultbox, _na.hostages_icon,
            }
            for i, leaf in ipairs(restore_leaves) do
                local v = leaf:visible()
                assert(v == true,
                    "RED: leaf #" .. i .. " must restore to visible=true, got "
                    .. tostring(v))
            end

            local nv_count_after = 0
            for _, e in ipairs(nv._entries or {}) do
                nv_count_after = nv_count_after + 1
            end
            assert(nv_count_after == 0,
                "RED: no NV records after disable, got "
                .. tostring(nv_count_after))

            assert(A._root_panel == nil,
                "RED: owned root must be removed after disable")
            assert(A._mounted == false,
                "RED: A._mounted must be false after disable")

            assert(_na.hud_panel:visible() == true,
                "RED: hud_panel must remain untouched after disable")
            assert(_na.third_party:visible() == true,
                "RED: third_party must remain untouched after disable")
            assert(_na.ap_text_panel:visible() == true,
                "RED: assault_panel text_panel must remain untouched")
            assert(_na.pnr_panel:visible() == false,
                "RED: pnr sentinel untouched after disable")
            assert(_na.casing_panel:visible() == false,
                "RED: casing sentinel untouched after disable")
            assert(_na.buffs_panel:visible() == false,
                "RED: buffs sentinel untouched after disable")
        ''')


class AssaultNativeRepelAfterAcquisitionTests(unittest.TestCase):
    """One repel-after-acquisition transition (RED).

    Mount + update acquires 14 NV targets. Then native PNR becomes active
    (corner._point_of_no_return=true, pnr_panel visible=true). A:update must
    release all NV records, restore text_panel alpha to 0.37, restore every
    static leaf exactly, hide the OWN root, leave native PNR visible=true,
    and leave thirdparty untouched.

    When the flag clears, A:update must reacquire the 14 NV targets, restore
    root visibility, and keep the same root/ticker identities (no structural
    changes).

    RED: update does not yet coordinate with native state.
    """

    def test_pnr_repel_releases_then_reacquires(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            assert(RT._root_panel, "RT._root_panel must exist after mount")

            local A = kyohud.hud.assault
            assert(A, "A must exist")
            assert(type(A.mount) == "function",
                "RED: A:mount must be a function")

            A:mount(managers.hud)
            assert(A._root_panel,
                "RED: A._root_panel must exist after mount")

            A:update(managers.hud, 1.0, 0.05)

            local nv = kyohud.hud.native_visibility
            local nv_count = 0
            for _, e in ipairs(nv._entries or {}) do
                nv_count = nv_count + 1
            end
            assert(nv_count == 14,
                "RED: expected exactly 14 NV entries after acquire, got "
                .. tostring(nv_count))

            local saved_root = A._root_panel
            local saved_ticker_a = A._ticker_a
            local saved_ticker_b = A._ticker_b
            local saved_ticker_panel = A._ticker_panel
            local saved_hostages_prim = A._hostages_prim
            local saved_converted_prim = A._converted_prim

            local corner = managers.hud._hud_assault_corner
            corner._point_of_no_return = true
            _na.pnr_panel:set_visible(true)

            A:update(managers.hud, 2.0, 0.05)

            local nv_count_repel = 0
            for _, e in ipairs(nv._entries or {}) do
                nv_count_repel = nv_count_repel + 1
            end
            assert(nv_count_repel == 0,
                "RED: all NV records must be released on repel, got "
                .. tostring(nv_count_repel))

            local tp_alpha_repel = _na.text_panel:alpha()
            assert(math.abs(tp_alpha_repel - 0.37) < 0.01,
                "RED: text_panel alpha must restore to 0.37 on repel, got "
                .. tostring(tp_alpha_repel))

            local restore_leaves = {
                _na.bg_leaf, _na.left_top, _na.left_bottom, _na.right_top,
                _na.h_bg, _na.h_lt, _na.h_lb, _na.h_rt, _na.h_rb,
                _na.num_hostages, _na.icon_assaultbox, _na.hostages_icon,
            }
            for i, leaf in ipairs(restore_leaves) do
                local v = leaf:visible()
                assert(v == true,
                    "RED: leaf #" .. i .. " must restore to visible=true on repel, got "
                    .. tostring(v))
            end
            assert(_na.right_bottom:visible() == false,
                "RED: decorative leaf (originally false) must stay false on repel")

            local root_vis_repel = A._root_panel:visible()
            assert(root_vis_repel == false,
                "RED: OWN root must be hidden on repel, got "
                .. tostring(root_vis_repel))

            assert(_na.pnr_panel:visible() == true,
                "RED: native PNR must stay visible=true on repel")

            assert(_na.third_party:visible() == true,
                "RED: third_party must remain untouched on repel")
            assert(_na.ap_text_panel:visible() == true,
                "RED: assault_panel text_panel must remain untouched on repel")

            corner._point_of_no_return = false
            _na.pnr_panel:set_visible(false)

            A:update(managers.hud, 3.0, 0.05)

            local nv_count_reacquire = 0
            for _, e in ipairs(nv._entries or {}) do
                nv_count_reacquire = nv_count_reacquire + 1
            end
            assert(nv_count_reacquire == 14,
                "RED: 14 NV records must be reacquired after flag clear, got "
                .. tostring(nv_count_reacquire))

            local root_vis_reacquire = A._root_panel:visible()
            assert(root_vis_reacquire == true,
                "RED: OWN root must be visible again after flag clear, got "
                .. tostring(root_vis_reacquire))

            assert(rawequal(A._root_panel, saved_root),
                "RED: root identity must be preserved (rawequal)")
            assert(rawequal(A._ticker_a, saved_ticker_a),
                "RED: ticker_a identity must be preserved (rawequal)")
            assert(rawequal(A._ticker_b, saved_ticker_b),
                "RED: ticker_b identity must be preserved (rawequal)")
            assert(rawequal(A._ticker_panel, saved_ticker_panel),
                "RED: ticker_panel identity must be preserved (rawequal)")
            assert(rawequal(A._hostages_prim, saved_hostages_prim),
                "RED: hostages_prim identity must be preserved (rawequal)")
            assert(rawequal(A._converted_prim, saved_converted_prim),
                "RED: converted_prim identity must be preserved (rawequal)")

            local tp_alpha_reacquire = _na.text_panel:alpha()
            assert(math.abs(tp_alpha_reacquire - 0) < 0.001,
                "RED: text_panel alpha must be 0 again after reacquire, got "
                .. tostring(tp_alpha_reacquire))

            for i, leaf in ipairs(restore_leaves) do
                local v = leaf:visible()
                assert(v == false,
                    "RED: static leaf #" .. i .. " must be visible=false after reacquire, got "
                    .. tostring(v))
            end

            assert(_na.pnr_panel:visible() == false,
                "RED: native PNR must remain visible=false after flag clear")
            assert(_na.third_party:visible() == true,
                "RED: third_party must remain untouched after flag clear")
        ''')


class AssaultOwnedRenderLossRecoveryTests(unittest.TestCase):
    """One owned-render loss/recovery transition (RED).

    Mount + update acquires 14 NV targets. Save root and ticker_a identities
    plus desired text. Corrupt actual ticker_a text to "CORRUPTED" and replace
    its set_text with no-op. Assert _verify_render returns false (must compare
    desired text, not merely nonempty). Invoke update -> release all records,
    restore text_panel alpha to 0.37, hide OWN root. Restore original set_text.
    Invoke update twice -> recovers desired text via owning update, root visible,
    same identities, 14 entries. Mark ticker_b _alive=false, assert _verify_render
    returns false, restore _alive=true.

    RED: _verify_render does not yet compare actual vs desired text.
    """

    def test_text_corruption_loss_then_recovery(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            assert(RT._root_panel, "RT._root_panel must exist after mount")

            local A = kyohud.hud.assault
            assert(A, "A must exist")
            assert(type(A.mount) == "function",
                "RED: A:mount must be a function")

            A:mount(managers.hud)
            assert(A._root_panel,
                "RED: A._root_panel must exist after mount")

            A:update(managers.hud, 1.0, 0.05)

            local nv = kyohud.hud.native_visibility
            local nv_count = 0
            for _, e in ipairs(nv._entries or {}) do
                nv_count = nv_count + 1
            end
            assert(nv_count == 14,
                "RED: expected exactly 14 NV entries after acquire, got "
                .. tostring(nv_count))

            local saved_root = A._root_panel
            local saved_ticker_a = A._ticker_a
            local saved_ticker_b = A._ticker_b
            local desired_text = A._ticker_a:text()
            assert(type(desired_text) == "string" and #desired_text > 0,
                "RED: desired ticker text must be nonempty")

            local original_set_text = A._ticker_a.set_text
            A._ticker_a:set_text("CORRUPTED")
            function A._ticker_a:set_text(str) end

            local vr_corrupt = A:_verify_render()
            assert(vr_corrupt == false,
                "RED: _verify_render must detect text corruption (actual != desired), got true")

            A:update(managers.hud, 2.0, 0.05)

            local nv_count_release = 0
            for _, e in ipairs(nv._entries or {}) do
                nv_count_release = nv_count_release + 1
            end
            assert(nv_count_release == 0,
                "RED: all NV records must be released on render failure, got "
                .. tostring(nv_count_release))

            local tp_alpha_release = _na.text_panel:alpha()
            assert(math.abs(tp_alpha_release - 0.37) < 0.01,
                "RED: text_panel alpha must restore to 0.37 on render failure, got "
                .. tostring(tp_alpha_release))

            local root_vis_release = A._root_panel:visible()
            assert(root_vis_release == false,
                "RED: OWN root must be hidden on render failure, got "
                .. tostring(root_vis_release))

            A._ticker_a.set_text = original_set_text

            A:update(managers.hud, 3.0, 0.05)
            A:update(managers.hud, 4.0, 0.05)

            local nv_count_recover = 0
            for _, e in ipairs(nv._entries or {}) do
                nv_count_recover = nv_count_recover + 1
            end
            assert(nv_count_recover == 14,
                "RED: 14 NV records must be reacquired after recovery, got "
                .. tostring(nv_count_recover))

            local root_vis_recover = A._root_panel:visible()
            assert(root_vis_recover == true,
                "RED: OWN root must be visible after recovery, got "
                .. tostring(root_vis_recover))

            assert(rawequal(A._root_panel, saved_root),
                "RED: root identity must be preserved (rawequal)")
            assert(rawequal(A._ticker_a, saved_ticker_a),
                "RED: ticker_a identity must be preserved (rawequal)")
            assert(rawequal(A._ticker_b, saved_ticker_b),
                "RED: ticker_b identity must be preserved (rawequal)")

            local recovered_text = A._ticker_a:text()
            assert(recovered_text == desired_text,
                "RED: recovered text must match desired text, got "
                .. tostring(recovered_text) .. " expected " .. tostring(desired_text))

            A._ticker_b._alive = false
            local vr_dead_b = A:_verify_render()
            assert(vr_dead_b == false,
                "RED: _verify_render must detect dead ticker_b primitive, got true")
            A._ticker_b._alive = true
        ''')


class AssaultNativeConflictTransitionTests(unittest.TestCase):
    """One conflict transition (RED).

    Mount/update acquires 14 NV targets. External actor sets text_panel alpha
    to 0.61 (conflicting with recorded baseline 0.37). A:update detects the
    conflict, releases all NV records, restores other leaves, keeps alpha at
    0.61, hides OWN root, _verify_render false. Repeated updates must not
    re-mask. Disable then re-enable clears conflict and acquires with latest
    baseline 0.61. Disable again restores alpha to 0.61.
    """

    def test_external_alpha_conflict_release_and_cycle(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")
        lua.execute('''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)
            local nv = kyohud.hud.native_visibility
            local function nvc()
                local n = 0
                for _ in ipairs(nv._entries or {}) do n = n + 1 end
                return n
            end
            assert(nvc() == 14,
                "RED: 14 NV entries after acquire, got " .. nvc())
            local saved_root = A._root_panel
            _na.text_panel:set_alpha(0.61)
            A:update(managers.hud, 2.0, 0.05)
            assert(math.abs(_na.text_panel:alpha() - 0.61) < 0.01,
                "RED: alpha must remain 0.61 after conflict, got "
                .. tostring(_na.text_panel:alpha()))
            local leaves = {
                _na.bg_leaf, _na.left_top, _na.left_bottom, _na.right_top,
                _na.h_bg, _na.h_lt, _na.h_lb, _na.h_rt, _na.h_rb,
                _na.num_hostages, _na.icon_assaultbox, _na.hostages_icon,
            }
            for i, l in ipairs(leaves) do
                assert(l:visible() == true,
                    "RED: leaf #" .. i .. " must restore on conflict, got "
                    .. tostring(l:visible()))
            end
            assert(_na.right_bottom:visible() == false,
                "RED: decorative leaf must stay false on conflict")
            assert(nvc() == 0,
                "RED: NV entries must be 0 after conflict, got " .. nvc())
            assert(A._root_panel:visible() == false,
                "RED: OWN root must be hidden after conflict")
            assert(A:_verify_render() == false,
                "RED: _verify_render must be false after conflict")
            assert(rawequal(A._root_panel, saved_root),
                "RED: root identity must be preserved (rawequal)")
            A:update(managers.hud, 3.0, 0.05)
            assert(math.abs(_na.text_panel:alpha() - 0.61) < 0.01,
                "RED: alpha must stay 0.61 on update3")
            assert(nvc() == 0,
                "RED: NV must stay 0 on update3")
            A:update(managers.hud, 4.0, 0.05)
            assert(nvc() == 0,
                "RED: update4 must not re-mask conflicting corner")
            kyohud.settings.enable_assault = false
            A:refresh_settings(managers.hud)
            assert(math.abs(_na.text_panel:alpha() - 0.61) < 0.01,
                "RED: alpha must be 0.61 after disable")
            kyohud.settings.enable_assault = true
            A:refresh_settings(managers.hud)
            assert(nvc() == 14,
                "RED: re-enable must acquire 14 entries with baseline 0.61, got "
                .. nvc())
            assert(math.abs(_na.text_panel:alpha() - 0) < 0.001,
                "RED: text_panel alpha must be 0 after re-acquire")
            kyohud.settings.enable_assault = false
            A:refresh_settings(managers.hud)
            assert(math.abs(_na.text_panel:alpha() - 0.61) < 0.01,
                "RED: alpha must restore to 0.61 on final disable, got "
                .. tostring(_na.text_panel:alpha()))
        ''')


class AssaultRestorationRetryTests(unittest.TestCase):
    """One restoration retry test (RED).

    positive_acquire14 helper: mount+update acquires 14 targets.
    Override tp.set_alpha to no-op for 0.37 only. Disable -> alpha stays 0,
    1 pending alpha entry, _native_targets preserved. Restore setter,
    update(2) while disabled -> retries restoration, alpha 0.37, NV 0,
    native_targets nil, no root recreation.
    """

    def test_restoration_retry_after_setter_restore(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")
        lua.execute('''
            local function positive_acquire14()
                local RT = kyohud.hud.runtime
                RT:mount(managers.hud)
                local A = kyohud.hud.assault
                A:mount(managers.hud)
                A:update(managers.hud, 1.0, 0.05)
                local nv = kyohud.hud.native_visibility
                local n = 0
                for _ in ipairs(nv._entries or {}) do n = n + 1 end
                assert(n == 14, "expected 14 NV entries, got " .. n)
                return A, nv
            end
            local A, nv = positive_acquire14()
            local tp = A._native_targets.text_panel
            local saved_setter = tp.set_alpha
            local saved_gen = A._native_generation
            function tp:set_alpha(v) if v ~= 0.37 then self._alpha = v end end
            kyohud.settings.enable_assault = false
            A:refresh_settings(managers.hud)
            assert(A._root_panel == nil, "owned root must be removed")
            assert(math.abs(tp:alpha() - 0) < 0.001, "tp alpha must remain 0, got " .. tp:alpha())
            local alpha_n, vis_n = 0, 0
            for _, e in ipairs(nv._entries or {}) do
                if e.property == "alpha" then alpha_n = alpha_n + 1
                elseif e.property == "visible" then vis_n = vis_n + 1 end
            end
            assert(alpha_n == 1, "exactly 1 pending alpha entry, got " .. alpha_n)
            assert(vis_n == 0, "0 visible entries after restore, got " .. vis_n)
            assert(A._native_targets and A._native_targets.text_panel == tp, "_native_targets.text_panel same tp")
            assert(A._native_generation == saved_gen, "native_generation unchanged")
            tp.set_alpha = saved_setter
            A:update(managers.hud, 2.0, 0.05)
            assert(math.abs(tp:alpha() - 0.37) < 0.01, "tp alpha must restore to 0.37, got " .. tp:alpha())
            local n_after = 0
            for _ in ipairs(nv._entries or {}) do n_after = n_after + 1 end
            assert(n_after == 0, "NV must be 0 after retry, got " .. n_after)
            assert(A._native_targets == nil, "native_targets must be nil after retry")
            assert(A._root_panel == nil, "no owned root recreation")
        ''')


class AssaultExactParentQualificationTests(unittest.TestCase):
    """One exact-parent qualification test (RED).

    Resolver must verify each target's actual parent matches the expected
    structural parent. Mismatch before mount prevents acquisition; restoring
    the parent allows re-acquisition. Mid-hold parent moves release all
    records; repair re-acquires with the same root identity.
    """

    def test_parent_mismatch_prevents_acquire_release_reacquire(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")
        lua.execute('''
            local bg_real = _na.bg_box._parent
            _na.bg_box._parent = _na.third_party
            local tp_vis0 = _na.third_party:visible()

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            local nv = kyohud.hud.native_visibility
            local function nvc()
                local n = 0
                for _ in ipairs(nv._entries or {}) do n = n + 1 end
                return n
            end
            assert(nvc() == 0,
                "RED: NV must be 0 with bg_box parent mismatch, got " .. nvc())
            assert(A._root_panel:visible() == false,
                "RED: OWN root must be hidden on parent mismatch")
            assert(_na.third_party:visible() == tp_vis0,
                "RED: third_party must not change on mismatch")

            _na.bg_box._parent = bg_real
            A:update(managers.hud, 2.0, 0.05)
            assert(nvc() == 14,
                "RED: 14 NV entries after bg_box parent restore, got " .. nvc())
            local saved_root = A._root_panel

            local nh_real = _na.num_hostages._parent
            _na.num_hostages._parent = _na.third_party
            local tp_vis1 = _na.third_party:visible()
            A:update(managers.hud, 3.0, 0.05)
            assert(nvc() == 0,
                "RED: NV must be 0 after num_hostages parent move, got " .. nvc())
            assert(math.abs(_na.text_panel:alpha() - 0.37) < 0.01,
                "RED: text_panel alpha must restore to 0.37 on release, got "
                .. tostring(_na.text_panel:alpha()))
            assert(A._root_panel:visible() == false,
                "RED: OWN root must be hidden after release")
            assert(_na.third_party:visible() == tp_vis1,
                "RED: third_party must be unchanged on release")

            _na.num_hostages._parent = nh_real
            A:update(managers.hud, 4.0, 0.05)
            assert(nvc() == 14,
                "RED: 14 NV entries after num_hostages repair, got " .. nvc())
            assert(rawequal(A._root_panel, saved_root),
                "RED: root identity must be preserved after repair")
        ''')


if __name__ == "__main__":
    unittest.main()
