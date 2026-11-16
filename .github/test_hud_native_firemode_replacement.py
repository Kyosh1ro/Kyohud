"""H5 native firemode replacement for every known local weapon slot.

Both fixed firemode_single/firemode_auto leaves are alpha-leased for every
known present coherent local weapon slot, independent of the selected slot.
Unknown mode restores only its own slot; empty/foreign/wrong-parent leaves
stay native. RED until production extends the H5 weapon target collection.
"""
import unittest

from test_hud_local_h5_lifecycle import _local_runtime

FIREMODE_SETUP = r'''
_LOCAL_PRIMARY = _WEAPON_PRIMARY_BG:parent()
_LOCAL_SECONDARY = _WEAPON_SECONDARY_BG:parent()
_PSEL = _LOCAL_PRIMARY:child("weapon_selection")
_SSEL = _LOCAL_SECONDARY:child("weapon_selection")
local function mode(parent, name, alpha, visible)
    local leaf = parent:bitmap({name = name})
    leaf:set_shape(0, 0, 12, 32); leaf:set_alpha(alpha); leaf:set_visible(visible)
    return leaf
end
_P_SINGLE = mode(_PSEL, "firemode_single", .63, true)
_P_AUTO = mode(_PSEL, "firemode_auto", .81, false)
_P_EXTRA = mode(_PSEL, "firemode_burst", .42, true)
_S_SINGLE = mode(_SSEL, "firemode_single", .63, false)
_S_AUTO = mode(_SSEL, "firemode_auto", .81, true)
_parent_writes = 0
local function spy(parent)
    for _, name in ipairs({"set_alpha", "set_visible", "set_shape",
        "set_color", "clear", "remove", "set_parent"}) do
        local original = parent[name]
        if type(original) == "function" then
            parent[name] = function(self, ...)
                _parent_writes = _parent_writes + 1; return original(self, ...)
            end
        end
    end
end
spy(_PSEL); spy(_SSEL)
'''


class NativeFiremodeReplacementTests(unittest.TestCase):
    def test_selected_firemode_alpha_lease_switch_restore_and_requalify(self):
        """Lease both fixed leaves on every known slot, then switch and restore.

        Native visible is toggled independently, an unknown mode restores only
        that slot's two leaves, a fresh same-name leaf is requalified, a
        foreign-name and a wrong-parent leaf stay native, switching slots keeps
        every known slot masked, and disabling weapons or the foundation
        restores every exact alpha.
        """
        lua = _local_runtime()
        lua.execute(FIREMODE_SETUP + r'''
            local W, R = kyohud.hud.weapons, kyohud.hud.runtime
            local nv = kyohud.hud.native_visibility
            local writes = 0
            local function step(t)
                _parent_writes = 0; R:update(mgr, t, .1)
                writes = writes + _parent_writes
            end
            local function refresh()
                _parent_writes = 0; R:refresh_settings(mgr)
                writes = writes + _parent_writes
            end
            local function member(leaf)
                local state = R._h5_groups and R._h5_groups["local_p_w"]
                for _, target in ipairs(state and state.targets or {}) do
                    if target == leaf then return true end
                end
                return false
            end
            local function lease(leaf)
                return nv._whitelist[leaf] ~= nil and nv._whitelist[leaf].alpha == true
            end

            step(1.2); step(1.3)
            _selected = W._current_snapshot and W._current_snapshot.selected
            _verified = W:verify()
            _positive = _P_SINGLE:alpha() == 0 and _P_AUTO:alpha() == 0
                and _S_SINGLE:alpha() == 0 and _S_AUTO:alpha() == 0
                and lease(_P_SINGLE) and lease(_P_AUTO)
                and lease(_S_SINGLE) and lease(_S_AUTO)
                and member(_P_SINGLE) and member(_P_AUTO)
                and member(_S_SINGLE) and member(_S_AUTO)
                and _P_EXTRA:alpha() == .42
                and nv._whitelist[_P_EXTRA] == nil

            _P_SINGLE:set_visible(false); step(1.4)
            _hidden = _P_SINGLE:visible() == false and _P_SINGLE:alpha() == 0
                and lease(_P_SINGLE)
            _P_SINGLE:set_visible(true); step(1.5)
            _shown = _P_SINGLE:visible() == true and _P_SINGLE:alpha() == 0
                and lease(_P_SINGLE)
            _visibility = _hidden and _shown

            local base2 = inventory:available_selections()[2].unit:base()
            base2:_native_set_fire_mode("mystery"); step(2.1)
            _unknown = _P_SINGLE:alpha() == .63 and _P_AUTO:alpha() == .81
                and nv._whitelist[_P_SINGLE] == nil
                and nv._whitelist[_P_AUTO] == nil
                and not member(_P_SINGLE) and not member(_P_AUTO)
                and _S_SINGLE:alpha() == 0 and _S_AUTO:alpha() == 0
                and lease(_S_SINGLE) and lease(_S_AUTO)
                and _P_EXTRA:alpha() == .42
            base2:_native_set_fire_mode(""); step(2.4)
            _empty = _P_SINGLE:alpha() == .63 and _P_AUTO:alpha() == .81
                and _S_SINGLE:alpha() == 0 and _S_AUTO:alpha() == 0
                and _P_EXTRA:alpha() == .42
            base2:_native_set_fire_mode("single"); step(2.7)
            _restored = _P_SINGLE:alpha() == 0 and _P_AUTO:alpha() == 0
                and lease(_P_SINGLE) and lease(_P_AUTO)

            _PSEL:remove(_P_SINGLE)
            _P_SINGLE = _PSEL:bitmap({name = "firemode_single"})
            _P_SINGLE:set_shape(0, 0, 12, 32); _P_SINGLE:set_alpha(.63)
            _P_SINGLE:set_visible(true)
            local decoy = _LOCAL_PRIMARY:bitmap({name = "firemode_single"})
            decoy:set_shape(0, 0, 12, 32); decoy:set_alpha(.63)
            decoy:set_visible(true)
            step(2.8)
            _replacement = _P_SINGLE:alpha() == 0 and _P_AUTO:alpha() == 0
                and lease(_P_SINGLE) and lease(_P_AUTO)
                and _S_SINGLE:alpha() == 0 and _S_AUTO:alpha() == 0
                and decoy:alpha() == .63 and nv._whitelist[decoy] == nil
                and _P_EXTRA:alpha() == .42

            inventory:_native_set_equipped(1); step(3.5)
            _selected_after = W._current_snapshot and W._current_snapshot.selected
            _switch = _S_AUTO:alpha() == 0 and _S_SINGLE:alpha() == 0
                and _P_SINGLE:alpha() == 0 and _P_AUTO:alpha() == 0
                and lease(_S_AUTO) and lease(_S_SINGLE)
                and lease(_P_SINGLE) and lease(_P_AUTO)
                and member(_S_AUTO) and member(_S_SINGLE)
                and member(_P_SINGLE) and member(_P_AUTO)
                and _P_EXTRA:alpha() == .42

            kyohud.settings.enable_weapons = false; refresh(); step(4.1)
            _w_restored = _S_SINGLE:alpha() == .63 and _S_AUTO:alpha() == .81
                and _P_SINGLE:alpha() == .63 and _P_AUTO:alpha() == .81
                and decoy:alpha() == .63 and _P_EXTRA:alpha() == .42
            kyohud.settings.enable_weapons = true; refresh(); step(4.7)
            _reacquired = _S_AUTO:alpha() == 0 and _S_SINGLE:alpha() == 0
                and _P_SINGLE:alpha() == 0 and _P_AUTO:alpha() == 0
                and lease(_S_AUTO) and lease(_S_SINGLE)
                and lease(_P_SINGLE) and lease(_P_AUTO)
            kyohud.settings.enable_hud_foundation = false; step(5.3)
            _foundation_restored = _S_SINGLE:alpha() == .63
                and _S_AUTO:alpha() == .81 and _P_SINGLE:alpha() == .63
                and _P_AUTO:alpha() == .81 and decoy:alpha() == .63
                and _P_EXTRA:alpha() == .42
            _writes = writes
        ''')
        g = lua.globals()
        self.assertEqual(int(g._selected), 2, "slot 2 must be selected initially")
        self.assertTrue(bool(g._verified), "the weapons render must be certified")
        self.assertTrue(bool(g._positive),
                        "both fixed leaves must be leased on every known coherent slot")
        self.assertTrue(bool(g._visibility), "native visible must stay independent")
        self.assertTrue(bool(g._unknown),
                        "unknown mode must restore only that slot's exact leaves")
        self.assertTrue(bool(g._empty),
                        "empty mode must restore only that slot's exact leaves")
        self.assertTrue(bool(g._restored),
                        "known mode must mask both fixed leaves again")
        self.assertTrue(bool(g._replacement),
                        "fresh same-name leaf must be requalified with its fixed sibling")
        self.assertEqual(int(g._selected_after), 1, "slot 1 must be selected after the switch")
        self.assertTrue(bool(g._switch),
                        "switch must keep both fixed leaves masked on every known slot")
        self.assertTrue(bool(g._w_restored), "disabling weapons must restore exact alphas")
        self.assertTrue(bool(g._reacquired),
                        "re-enabling weapons must mask both fixed leaves on every slot")
        self.assertTrue(bool(g._foundation_restored), "disabling foundation must restore exact alphas")
        self.assertEqual(float(g._writes), 0.0, "selection parents must never be mutated")
