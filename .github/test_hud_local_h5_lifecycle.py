"""Local player H5 group lifecycle: release, re-qualification, re-acquisition.

Scope: the local player slice of the H5 native-duplicate coordinator. The
runtime order under test is real: player/weapons/crew consumers first, then
_apply_native_priority (H4), then _coordinate_h5_native_duplicates (H5). H5
reads the owned root visibility after H4, so a frame hidden by native priority
releases local_p_p and restores the native leaves. When the native source no
longer hides the block, the next real polls must re-qualify the identity and
re-acquire the same primitives.

Fixture reuse: test_hud_crew_online_ammo._crew_lua (real crew stack),
RENDER_SETUP, ACTORS_PATH and the online_runtime install model from
test_hud_crew_online_native (R:mount/R:update on the same primitives). The
native inventory fixture and real weapons chunks are imported/loaded so the
local weapons H5 group exists as it does in game. No production monkeypatch,
no Python copy of Lua logic, no skip.
"""
import unittest

from test_hud_crew_online_ammo import _crew_lua, RENDER_SETUP, ACTORS_PATH, ROOT
from test_hud_weapons import NATIVE_INVENTORY_WEAPON_FIXTURE

WEAPON_COMPONENT_PATH = ROOT / "lua" / "hud" / "components" / "weapon.lua"
WEAPONS_PATH = ROOT / "lua" / "hud" / "weapons.lua"


def _local_runtime():
    """Build the real runtime with local player, weapons and crew consumers."""
    lua, ok = _crew_lua()
    assert ok

    lua.execute(NATIVE_INVENTORY_WEAPON_FIXTURE)
    lua.execute(WEAPON_COMPONENT_PATH.read_text(encoding="utf-8-sig"))
    weapons_src = WEAPONS_PATH.read_text(encoding="utf-8-sig")
    for context in ("lib/managers/hudmanagerpd2",
                    "lib/units/beings/player/playerinventory"):
        lua.globals().RequiredScript = context
        lua.execute(weapons_src)

    lua.execute(RENDER_SETUP)

    lua.execute(r'''
        local damage = {
            _health = 75, _health_max = 100, _armor = 20, _armor_max = 50,
            _revives = 1,
            get_real_health = function(self) return self._health end,
            _max_health = function(self) return self._health_max end,
            get_real_armor = function(self) return self._armor end,
            _max_armor = function(self) return self._armor_max end,
            get_revives = function(self) return self._revives end,
        }
        player_unit.inventory = function() return inventory end
        player_unit.current_state = function() return {name = "standard"} end
        player_unit.character_damage = function(self) return damage end
        managers.player.player_unit = function(self) return player_unit end
        managers.player.current_state = function(self) return "standard" end
        _G._local_damage = damage
    ''')

    # The base fixture records hooks; RENDER_SETUP wraps only later installs.
    # Reinstall the real revives callback through that wrapper so the genuine
    # native setter reaches actors, as documented by the online fixture.
    lua.execute("kyohud.hud._installed_hooks.KyohHUD_Actors_Revives=nil")
    # Native-shaped interaction channel: the RENDER_SETUP wrapper turns this
    # later reload into the real actors PostHook, so tests can end an
    # interaction through HUDManager:teammate_progress instead of a setter.
    lua.execute("kyohud.hud._installed_hooks.KyohHUD_Actors_Progress=nil")
    lua.execute(r'''
        function HUDManager:teammate_progress(peer_id, type_index, enabled,
            tweak_data_id, timer, success)
            _G._teammate_progress_calls = (_G._teammate_progress_calls or 0) + 1
            local leaf = _G._remote_progress_leaf
            if leaf and alive(leaf) then
                leaf:set_visible(enabled == true)
            end
        end
    ''')
    actors_src = ACTORS_PATH.read_text(encoding="utf-8-sig")
    for context in ("lib/managers/playermanager", "lib/managers/hudmanagerpd2"):
        lua.globals().RequiredScript = context
        lua.execute(actors_src)

    lua.execute(r'''
        kyohud.settings.enable_hud_foundation = true
        kyohud.settings.enable_player = true
        kyohud.settings.enable_crew = true
        kyohud.settings.enable_weapons = true
        kyohud.settings.enable_equipment = false
        kyohud.settings.hud_scale = 1.0
        _G.panel_double:set_shape(0, 0, 1920, 1080)

        managers.player.current_state = function(self) return "standard" end
        local unit1, base1 = make_weapon("new_m1014")
        base1:_native_set_ammo(8, 6, 32, 40)
        base1:_native_set_fire_mode("auto")
        inventory:_native_set_slot(1, unit1)
        local unit2, base2 = make_weapon("new_m16")
        base2:_native_set_ammo(30, 25, 120, 150)
        base2:_native_set_fire_mode("single")
        inventory:_native_set_slot(2, unit2)
        inventory:_native_set_equipped(2)

        mgr = managers.hud
        ACT = kyohud.hud.actors
        ACT:refresh_crew(mgr, 0)
        mgr:set_teammate_revives(2, 4)
        assert(ACT:get_crew_snapshot()[2].downs == 3,
            "qualified crew downs must be captured before mount")

        R = kyohud.hud.runtime
        R:mount(mgr)
        R:refresh_settings(mgr)

        P = kyohud.hud.player
        W = kyohud.hud.weapons
        C = kyohud.hud.crew
        _SLOT = HUDManager.PLAYER_PANEL
        assert(P._root and W._root and C._root, "owned roots must be mounted")

        local parents = {}
        local function remember(parent)
            parents[#parents + 1] = parent
            return parent
        end
        local function bitmap(parent, name, x, y, w, h, alpha, visible)
            local leaf = parent:bitmap({name = name})
            leaf:set_shape(x or 0, y or 0, w or 10, h or 10)
            leaf:set_alpha(alpha == nil and .7 or alpha)
            leaf:set_visible(visible == nil and true or visible)
            return leaf
        end
        local function label(parent, name, value, x, y, w, h, alpha, visible)
            local leaf = parent:text({name = name, text = value or ""})
            leaf:set_shape(x or 0, y or 0, w or 10, h or 10)
            leaf:set_alpha(alpha == nil and .7 or alpha)
            leaf:set_visible(visible == nil and true or visible)
            return leaf
        end
        local function container(parent, name, x, y, w, h, visible)
            local p = remember(parent:panel({name = name}))
            p:set_shape(x or 0, y or 0, w or 10, h or 10)
            p:set_visible(visible == nil and true or visible)
            return p
        end

        local px, py, pw, ph = P._root:x(), P._root:y(), P._root:w(), P._root:h()
        _LOCAL = remember(panel_double:panel({name = "local_h5_native_entry"}))
        _LOCAL:set_shape(px, py, pw, ph)
        _LOCAL:set_visible(true)

        _LOCAL_NAME = label(_LOCAL, "name", "Player", 10, 10, 100, 20, .7, true)
        _LOCAL_NAME_BG = bitmap(_LOCAL, "name_bg", 10, 10, 100, 20, .7, true)
        _LOCAL_CALLSIGN = bitmap(_LOCAL, "callsign", 0, 0, 20, 20, .7, true)
        _LOCAL_CALLSIGN_BG = bitmap(_LOCAL, "callsign_bg", 0, 0, 20, 20, .7, true)

        _LOCAL_PLAYER = container(_LOCAL, "player", 0, 0, pw, ph, true)
        _LOCAL_RADIAL = container(_LOCAL_PLAYER, "radial_health_panel",
            0, 0, pw, ph, true)
        _LOCAL_RADIAL_BG = bitmap(_LOCAL_RADIAL, "radial_bg", 0, 0, pw, ph, .7, true)
        _LOCAL_RADIAL_HEALTH = bitmap(_LOCAL_RADIAL, "radial_health",
            0, 0, pw, ph, .7, true)
        _LOCAL_RADIAL_SHIELD = bitmap(_LOCAL_RADIAL, "radial_shield",
            0, 0, pw, ph, .7, true)

        _LOCAL_REVIVE = container(_LOCAL_PLAYER, "revive_panel", 0, 0, pw, ph, true)
        _LOCAL_REVIVE_BG = bitmap(_LOCAL_REVIVE, "revive_bg",
            0, 0, 100, 30, .7, true)
        _LOCAL_REVIVE_AMOUNT = label(_LOCAL_REVIVE, "revive_amount", "1",
            0, 0, 100, 30, .7, true)
        _LOCAL_REVIVE_ARROW = bitmap(_LOCAL_REVIVE, "revive_arrow",
            0, 0, 30, 30, .7, true)

        local carry = container(_LOCAL_PLAYER, "carry_panel", 0, 0, 50, 20, false)
        carry:set_alpha(.7)
        local interact = label(_LOCAL_PLAYER, "interact_panel", "X",
            0, 0, 50, 20, .7, false)
        local custom = bitmap(_LOCAL_RADIAL, "radial_custom", 0, 0, 50, 20, .7, false)
        local ability = container(_LOCAL_RADIAL, "radial_ability", 0, 0, 50, 20, false)
        ability:set_alpha(.7)
        local rip = bitmap(_LOCAL_RADIAL, "radial_rip", 0, 0, 50, 20, .7, false)
        local rip_bg = bitmap(_LOCAL_RADIAL, "radial_rip_bg",
            0, 0, 50, 20, .7, false)
        rip_bg:set_color(Color(0, 0, 0))
        local shield_active = bitmap(_LOCAL_RADIAL, "radial_absorb_shield_active",
            0, 0, 50, 20, .7, false)
        local health_active = bitmap(_LOCAL_RADIAL, "radial_absorb_health_active",
            0, 0, 50, 20, .7, false)
        local info = bitmap(_LOCAL_RADIAL, "radial_info_meter",
            0, 0, 50, 20, .7, false)
        local info_bg = bitmap(_LOCAL_RADIAL, "radial_info_meter_bg",
            0, 0, 50, 20, .7, false)
        info_bg:set_color(Color(0, 0, 0))

        _DELAYED = container(_LOCAL_RADIAL, "radial_delayed_damage",
            0, 0, pw, ph, true)
        _DELAYED_ARMOR = bitmap(_DELAYED, "radial_delayed_damage_armor",
            0, 0, pw, ph, .7, false)
        _DELAYED_HEALTH = bitmap(_DELAYED, "radial_delayed_damage_health",
            0, 0, pw, ph, .7, false)
        local copr = container(_LOCAL_RADIAL, "copr_overlay_panel",
            0, 0, pw, ph, true)
        _CONDITION_TIMER = label(_LOCAL, "condition_timer", "10",
            0, 0, 50, 20, .5, false)
        _LOCAL_UNIQUE = bitmap(_LOCAL, "local_unique", 0, 0, 10, 10, .6, true)

        _LOCAL_WEAPONS = container(_LOCAL_PLAYER, "weapons_panel",
            0, 0, pw, ph, true)
        local function weapon_slot(name)
            local sp = container(_LOCAL_WEAPONS, name, 0, 0, 80, 32, true)
            local bg = bitmap(sp, "bg", 0, 0, 80, 32, .7, true)
            local clip = label(sp, "ammo_clip", "30", 0, 0, 40, 32, .7, true)
            local total = label(sp, "ammo_total", "90", 40, 0, 40, 32, .7, true)
            local sel = container(sp, "weapon_selection", 68, 0, 12, 32, true)
            local sel_bitmap = bitmap(sel, "weapon_selection", 0, 0, 12, 32, .7, true)
            return bg, clip, total, sel_bitmap
        end
        _WEAPON_SECONDARY_BG, _WEAPON_SECONDARY_CLIP, _WEAPON_SECONDARY_TOTAL,
            _WEAPON_SECONDARY_SEL = weapon_slot("secondary_weapon_panel")
        _WEAPON_PRIMARY_BG, _WEAPON_PRIMARY_CLIP, _WEAPON_PRIMARY_TOTAL,
            _WEAPON_PRIMARY_SEL = weapon_slot("primary_weapon_panel")

        _CREW_EP = remember(panel_double:panel({name = "crew_h5_native_entry"}))
        _CREW_EP:set_shape(0, 0, 280, 120)
        _CREW_EP:set_visible(true)
        _CREW_NAME = label(_CREW_EP, "name", "Crew", 10, 0, 80, 20, .7, true)
        _CREW_PLAYER = container(_CREW_EP, "player", 0, 0, 280, 120, true)
        _CREW_REVIVE = container(_CREW_PLAYER, "revive_panel",
            0, 0, 120, 30, true)
        _CREW_REVIVE_BG = bitmap(_CREW_REVIVE, "revive_bg", 0, 0, 120, 30, .7, true)
        _CREW_REVIVE_AMOUNT = label(_CREW_REVIVE, "revive_amount", "3",
            0, 0, 60, 30, .7, true)
        _CREW_REVIVE_ARROW = bitmap(_CREW_REVIVE, "revive_arrow",
            60, 0, 30, 30, .7, true)
        _CREW_UNIQUE = bitmap(_CREW_EP, "crew_unique", 0, 0, 10, 10, .6, true)

        local local_entry = mgr._teammate_panels[_SLOT] or {}
        local_entry._ai = false
        local_entry._peer_id = nil
        local_entry._panel = _LOCAL
        local_entry._special_equipment = {}
        mgr._teammate_panels[_SLOT] = local_entry

        local crew_entry = mgr._teammate_panels[2] or {_peer_id = 2, _ai = false}
        crew_entry._panel = _CREW_EP
        crew_entry._special_equipment = crew_entry._special_equipment or {}
        mgr._teammate_panels[2] = crew_entry

        _parent_writes = 0
        local function spy(parent)
            for _, name in ipairs({"set_alpha", "set_visible", "set_shape",
                "clear", "remove", "set_parent"}) do
                local original = parent[name]
                if type(original) == "function" then
                    parent[name] = function(self, ...)
                        _parent_writes = _parent_writes + 1
                        return original(self, ...)
                    end
                end
            end
        end
        for _, parent in ipairs(parents) do spy(parent) end

        R:update(mgr, 1.0, .1)
        R:update(mgr, 1.1, .1)
         ''')
    return lua


class LocalPlayerH5LifecycleTests(unittest.TestCase):
    def test_native_delayed_damage_releases_then_requalifies_local_group(self):
        """H4 delayed-damage priority releases local_p, then genuine polls recover it.

        The complete native local entry is installed at HUDManager.PLAYER_PANEL
        with player/radial_health_panel and every H4 leaf. Only the delayed
        damage armor/health leaves are active, visible and alpha>0 over the
        player block. A sustained real update hides the owned local root and H5
        releases local_p_p, restoring the native alpha values. Deactivating the
        source (visible=false, alpha=0) and polling beyond 0.5s must show the
        owned root again, re-qualify the identity and re-acquire the exact same
        native leaves at alpha 0.
        """
        lua = _local_runtime()
        lua.execute(r'''
            _positive_group = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _positive_label = P._h5_id_label ~= nil and P._h5_identity_verified == true
            _positive_p = P:verify()
            _positive_c = C:_verify_render()
            _positive_w = W:verify()
            _saved_name, _saved_rbg = _LOCAL_NAME, _LOCAL_RADIAL_BG
            _saved_rh, _saved_rs = _LOCAL_RADIAL_HEALTH, _LOCAL_RADIAL_SHIELD
            _saved_rev = _LOCAL_REVIVE_BG

            _parent_writes = 0
            _DELAYED_ARMOR:set_visible(true)
            _DELAYED_ARMOR:set_alpha(.7)
            _DELAYED_HEALTH:set_visible(true)
            _DELAYED_HEALTH:set_alpha(.7)
            R:update(mgr, 1.2, .1)
            R:update(mgr, 1.3, .1)

            _hidden = not P._root:visible()
            _group_released = (R._h5_groups == nil)
                or (R._h5_groups["local_p_p"] == nil)
            _name_restored = _LOCAL_NAME:alpha() == .7
            _radial_restored = _LOCAL_RADIAL_BG:alpha() == .7
                and _LOCAL_RADIAL_HEALTH:alpha() == .7
                and _LOCAL_RADIAL_SHIELD:alpha() == .7
            _revive_restored = _LOCAL_REVIVE_BG:alpha() == .7
            _label_before = P._h5_id_label
            _writes_active = _parent_writes

            _DELAYED_ARMOR:set_visible(false)
            _DELAYED_ARMOR:set_alpha(0)
            _DELAYED_HEALTH:set_visible(false)
            _DELAYED_HEALTH:set_alpha(0)
            _parent_writes = 0
            for i = 1, 7 do R:update(mgr, 1.3 + i * .1, .1) end

            _root_visible = P._root:visible()
            _p_verify = P:verify()
            _c_verify = C:_verify_render()
            _w_verify = W:verify()
            _group_back = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _same_leaves = (_LOCAL_NAME == _saved_name)
                and (_LOCAL_RADIAL_BG == _saved_rbg)
                and (_LOCAL_RADIAL_HEALTH == _saved_rh)
                and (_LOCAL_RADIAL_SHIELD == _saved_rs)
                and (_LOCAL_REVIVE_BG == _saved_rev)
            _same_label = (P._h5_id_label == _label_before)
            _requalified = P._h5_identity_verified == true
            _masked = _LOCAL_NAME:alpha() == 0
                and _LOCAL_RADIAL_BG:alpha() == 0
                and _LOCAL_RADIAL_HEALTH:alpha() == 0
                and _LOCAL_RADIAL_SHIELD:alpha() == 0
                and _LOCAL_REVIVE_BG:alpha() == 0
            _writes_recovery = _parent_writes
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._positive_group), "local_p_p must start acquired")
        self.assertTrue(bool(g._positive_label), "identity must start qualified")
        self.assertTrue(bool(g._positive_p), "player verifier must start positive")
        self.assertTrue(bool(g._positive_c), "crew verifier must start positive")
        self.assertTrue(bool(g._positive_w), "weapons verifier must start positive")

        self.assertTrue(bool(g._hidden), "native priority must hide the local root")
        self.assertTrue(bool(g._group_released), "H5 must release local_p_p")
        self.assertTrue(bool(g._name_restored), "native name alpha must be restored")
        self.assertTrue(bool(g._radial_restored), "native radial alphas must be restored")
        self.assertTrue(bool(g._revive_restored), "native revive alpha must be restored")
        self.assertEqual(float(g._writes_active), 0.0,
                         "native priority must not write parent setters")

        self.assertTrue(bool(g._root_visible), "recovered local root must be visible")
        self.assertTrue(bool(g._p_verify), "player verifier must recover")
        self.assertTrue(bool(g._c_verify), "crew verifier must stay positive")
        self.assertTrue(bool(g._w_verify), "weapons verifier must stay positive")
        self.assertTrue(bool(g._group_back), "H5 must re-acquire local_p_p")
        self.assertTrue(bool(g._same_leaves), "recovery must reuse the same native leaves")
        self.assertTrue(bool(g._same_label), "recovery must reuse the same identity label")
        self.assertTrue(bool(g._requalified), "identity must re-qualify")
        self.assertTrue(bool(g._masked), "covered leaves must return to alpha 0")
        self.assertEqual(float(g._writes_recovery), 0.0,
                         "recovery must not write parent setters")

    def test_transient_player_verify_failure_releases_then_restores_local_group(self):
        """A verified player geometry primitive fails, then repairs in place.

        The root geometry is corrupted and its setter bound no-op so the real
        player update cannot repair it in the same frame. H5 sees P.verify()
        fail, hides the owned root and releases local_p_p, restoring native
        alpha. Restoring the setter lets the real player update repair the
        geometry; the next update re-acquires the same native leaves and the
        same identity label at alpha 0.
        """
        lua = _local_runtime()
        lua.execute(r'''
            _positive_group = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _positive_label = P._h5_id_label ~= nil and P._h5_identity_verified == true
            _saved_name, _saved_rbg = _LOCAL_NAME, _LOCAL_RADIAL_BG
            _saved_rh, _saved_rs = _LOCAL_RADIAL_HEALTH, _LOCAL_RADIAL_SHIELD
            _saved_rev = _LOCAL_REVIVE_BG
            _label_before = P._h5_id_label

            local root = P._root
            local original_set_shape = root.set_shape
            root:set_shape(root:x() + 20, root:y(), root:w(), root:h())
            root.set_shape = function() end

            _parent_writes = 0
            R:update(mgr, 1.2, .1)

            _hidden = not root:visible()
            _p_verify_failed = P:verify() == false
            _group_released = (R._h5_groups == nil)
                or (R._h5_groups["local_p_p"] == nil)
            _name_restored = _LOCAL_NAME:alpha() == .7
            _radial_restored = _LOCAL_RADIAL_BG:alpha() == .7
                and _LOCAL_RADIAL_HEALTH:alpha() == .7
                and _LOCAL_RADIAL_SHIELD:alpha() == .7
            _revive_restored = _LOCAL_REVIVE_BG:alpha() == .7
            _writes_failed = _parent_writes

            root.set_shape = original_set_shape
            _parent_writes = 0
            R:update(mgr, 1.3, .1)

            _root_visible = root:visible()
            _p_verify = P:verify()
            _c_verify = C:_verify_render()
            _w_verify = W:verify()
            _group_back = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _same_leaves = (_LOCAL_NAME == _saved_name)
                and (_LOCAL_RADIAL_BG == _saved_rbg)
                and (_LOCAL_RADIAL_HEALTH == _saved_rh)
                and (_LOCAL_RADIAL_SHIELD == _saved_rs)
                and (_LOCAL_REVIVE_BG == _saved_rev)
            _same_label = (P._h5_id_label == _label_before)
            _requalified = P._h5_identity_verified == true
            _masked = _LOCAL_NAME:alpha() == 0
                and _LOCAL_RADIAL_BG:alpha() == 0
                and _LOCAL_RADIAL_HEALTH:alpha() == 0
                and _LOCAL_RADIAL_SHIELD:alpha() == 0
                and _LOCAL_REVIVE_BG:alpha() == 0
            _writes_recovery = _parent_writes
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._positive_group), "local_p_p must start acquired")
        self.assertTrue(bool(g._positive_label), "identity must start qualified")

        self.assertTrue(bool(g._hidden), "failed player verifier must hide the root")
        self.assertTrue(bool(g._p_verify_failed), "player verifier must report failure")
        self.assertTrue(bool(g._group_released), "H5 must release local_p_p")
        self.assertTrue(bool(g._name_restored), "native name alpha must be restored")
        self.assertTrue(bool(g._radial_restored), "native radial alphas must be restored")
        self.assertTrue(bool(g._revive_restored), "native revive alpha must be restored")
        self.assertEqual(float(g._writes_failed), 0.0,
                         "failure path must not write parent setters")

        self.assertTrue(bool(g._root_visible), "repaired root must be visible")
        self.assertTrue(bool(g._p_verify), "player verifier must recover")
        self.assertTrue(bool(g._c_verify), "crew verifier must stay positive")
        self.assertTrue(bool(g._w_verify), "weapons verifier must stay positive")
        self.assertTrue(bool(g._group_back), "H5 must re-acquire local_p_p")
        self.assertTrue(bool(g._same_leaves), "recovery must reuse the same native leaves")
        self.assertTrue(bool(g._same_label), "recovery must reuse the same identity label")
        self.assertTrue(bool(g._requalified), "identity must re-qualify")
        self.assertTrue(bool(g._masked), "covered leaves must return to alpha 0")
        self.assertEqual(float(g._writes_recovery), 0.0,
                         "recovery must not write parent setters")

    def test_actor_health_armor_and_real_revive_channel_release_and_reacquire(self):
        """Health/armor validity and the genuine revives channel gate radial/revive leaves.

        Invalidating the local damage maxima removes radial_bg/health/shield
        from the collected targets, so H5 releases those native alphas while the
        retained identity stays reusable. Restoring the source re-acquires the
        same radial primitives. Clearing revives makes downs unknown and releases the
        revive leaves; the genuine HUDManager:set_teammate_revives callback
        (installed through the wrapping fixture) republishes known downs and the
        same revive primitives are covered again.
        """
        lua = _local_runtime()
        lua.execute(r'''
            _positive_group = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _positive_label = P._h5_id_label ~= nil and P._h5_identity_verified == true
            _saved_rbg, _saved_rh = _LOCAL_RADIAL_BG, _LOCAL_RADIAL_HEALTH
            _saved_rs = _LOCAL_RADIAL_SHIELD
            _saved_rev_bg, _saved_rev_amt = _LOCAL_REVIVE_BG, _LOCAL_REVIVE_AMOUNT
            _saved_rev_arrow = _LOCAL_REVIVE_ARROW
            local cd = managers.player:player_unit():character_damage()
            local saved_hmax, saved_amax, saved_revives = cd._health_max,
                cd._armor_max, cd._revives

            _parent_writes = 0
            cd._health_max = 0
            cd._armor_max = 0
            R:update(mgr, 1.2, .1)

            _radial_released = _LOCAL_RADIAL_BG:alpha() == .7
                and _LOCAL_RADIAL_HEALTH:alpha() == .7
                and _LOCAL_RADIAL_SHIELD:alpha() == .7
            _writes_invalid = _parent_writes

            cd._health_max = saved_hmax
            cd._armor_max = saved_amax
            _parent_writes = 0
            R:update(mgr, 1.3, .1)

            _radial_back = _LOCAL_RADIAL_BG:alpha() == 0
                and _LOCAL_RADIAL_HEALTH:alpha() == 0
                and _LOCAL_RADIAL_SHIELD:alpha() == 0
            _same_radial = (_LOCAL_RADIAL_BG == _saved_rbg)
                and (_LOCAL_RADIAL_HEALTH == _saved_rh)
                and (_LOCAL_RADIAL_SHIELD == _saved_rs)
            _writes_radial = _parent_writes

            cd._revives = nil
            _parent_writes = 0
            R:update(mgr, 1.4, .1)

            _revive_released = _LOCAL_REVIVE_BG:alpha() == .7
                and _LOCAL_REVIVE_AMOUNT:alpha() == .7
                and _LOCAL_REVIVE_ARROW:alpha() == .7
            _downs_unknown = P._exp_downs_text == "--"
            _writes_unknown = _parent_writes

            cd._revives = 4
            mgr:set_teammate_revives(_SLOT, 4)
            local snap = ACT:get_actor(_SLOT)
            _channel_downs = snap and snap.downs or nil
            _parent_writes = 0
            R:update(mgr, 1.5, .1)

            _revive_back = _LOCAL_REVIVE_BG:alpha() == 0
                and _LOCAL_REVIVE_AMOUNT:alpha() == 0
                and _LOCAL_REVIVE_ARROW:alpha() == 0
            _same_revive = (_LOCAL_REVIVE_BG == _saved_rev_bg)
                and (_LOCAL_REVIVE_AMOUNT == _saved_rev_amt)
                and (_LOCAL_REVIVE_ARROW == _saved_rev_arrow)
            _root_visible = P._root:visible()
            _p_verify = P:verify()
            _c_verify = C:_verify_render()
            _w_verify = W:verify()
            _group_back = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _identity_same = P._h5_id_label ~= nil
                and P._h5_identity_verified == true
            _writes_final = _parent_writes
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._positive_group), "local_p_p must start acquired")
        self.assertTrue(bool(g._positive_label), "identity must start qualified")

        self.assertTrue(bool(g._radial_released),
                        "invalid health/armor must release radial natives")
        self.assertEqual(float(g._writes_invalid), 0.0,
                         "invalid metrics must not write parent setters")

        self.assertTrue(bool(g._radial_back), "valid health/armor must re-acquire radials")
        self.assertTrue(bool(g._same_radial), "radial recovery must reuse the same primitives")
        self.assertEqual(float(g._writes_radial), 0.0,
                         "radial recovery must not write parent setters")

        self.assertTrue(bool(g._revive_released), "unknown downs must release revive natives")
        self.assertTrue(bool(g._downs_unknown), "unknown downs must render the unknown marker")
        self.assertEqual(float(g._writes_unknown), 0.0,
                         "unknown downs must not write parent setters")
        self.assertEqual(float(g._channel_downs), 3.0,
                         "the genuine revives channel must republish known downs")

        self.assertTrue(bool(g._revive_back), "known downs must re-acquire revive natives")
        self.assertTrue(bool(g._same_revive), "revive recovery must reuse the same primitives")
        self.assertTrue(bool(g._root_visible), "local root must remain visible")
        self.assertTrue(bool(g._p_verify), "player verifier must stay positive")
        self.assertTrue(bool(g._c_verify), "crew verifier must stay positive")
        self.assertTrue(bool(g._w_verify), "weapons verifier must stay positive")
        self.assertTrue(bool(g._group_back), "local_p_p must remain acquired")
        self.assertTrue(bool(g._identity_same), "identity must keep the same certified label")
        self.assertEqual(float(g._writes_final), 0.0,
                         "revive recovery must not write parent setters")

    def test_crew_and_weapon_groups_survive_local_group_transitions(self):
        """Crew and weapons H5 groups stay leased while local_p releases and returns.

        A direct read-only H5 pass must not deep-copy public crew snapshots. Then
        a transient player verifier failure releases only local_p_p: crew_2 and
        local_p_w keep the same state tables, their covered native leaves remain
        alpha 0 and the unrelated native leaves keep their alpha. Repairing the
        player primitive re-acquires local_p_p without disturbing crew/weapons.
        """
        lua = _local_runtime()
        lua.execute(r'''
            _positive_group = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _positive_w = R._h5_groups and R._h5_groups["local_p_w"] ~= nil
            _positive_crew = R._h5_groups and R._h5_groups["crew_2"] ~= nil
            _w_state = R._h5_groups and R._h5_groups["local_p_w"] or nil
            _crew_state = R._h5_groups and R._h5_groups["crew_2"] or nil
            _saved_w = {_WEAPON_PRIMARY_BG, _WEAPON_PRIMARY_CLIP,
                _WEAPON_PRIMARY_TOTAL, _WEAPON_PRIMARY_SEL,
                _WEAPON_SECONDARY_BG, _WEAPON_SECONDARY_CLIP,
                _WEAPON_SECONDARY_TOTAL, _WEAPON_SECONDARY_SEL}
            _saved_crew_name, _saved_crew_bg = _CREW_NAME, _CREW_REVIVE_BG
            _crew_unique_alpha = _CREW_UNIQUE:alpha()
            _local_unique_alpha = _LOCAL_UNIQUE:alpha()

            local original_snapshot = ACT.get_crew_snapshot
            _snapshot_calls = 0
            ACT.get_crew_snapshot = function(self, ...)
                _snapshot_calls = _snapshot_calls + 1
                return original_snapshot(self, ...)
            end
            _parent_writes = 0
            R:_coordinate_h5_native_duplicates()
            ACT.get_crew_snapshot = original_snapshot
            _deepcopies = _snapshot_calls
            _writes_readonly = _parent_writes

            local root = P._root
            local original_set_shape = root.set_shape
            root:set_shape(root:x() + 20, root:y(), root:w(), root:h())
            root.set_shape = function() end

            _parent_writes = 0
            R:update(mgr, 1.2, .1)

            _local_released = (R._h5_groups == nil)
                or (R._h5_groups["local_p_p"] == nil)
            _w_same = R._h5_groups and R._h5_groups["local_p_w"] == _w_state
            _crew_same = R._h5_groups and R._h5_groups["crew_2"] == _crew_state
            _w_masked = _WEAPON_PRIMARY_BG:alpha() == 0
                and _WEAPON_PRIMARY_CLIP:alpha() == 0
                and _WEAPON_PRIMARY_TOTAL:alpha() == 0
                and _WEAPON_PRIMARY_SEL:alpha() == 0
                and _WEAPON_SECONDARY_BG:alpha() == 0
                and _WEAPON_SECONDARY_CLIP:alpha() == 0
                and _WEAPON_SECONDARY_TOTAL:alpha() == 0
                and _WEAPON_SECONDARY_SEL:alpha() == 0
            _crew_masked = _CREW_NAME:alpha() == 0
                and _CREW_REVIVE_BG:alpha() == 0
            _uniques = _CREW_UNIQUE:alpha() == _crew_unique_alpha
                and _LOCAL_UNIQUE:alpha() == _local_unique_alpha
                and _CONDITION_TIMER:alpha() == .5
            _writes_failed = _parent_writes

            root.set_shape = original_set_shape
            _parent_writes = 0
            R:update(mgr, 1.3, .1)

            _local_back = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _w_same_after = R._h5_groups and R._h5_groups["local_p_w"] == _w_state
            _crew_same_after = R._h5_groups and R._h5_groups["crew_2"] == _crew_state
            _same_w = _WEAPON_PRIMARY_BG == _saved_w[1]
                and _WEAPON_PRIMARY_CLIP == _saved_w[2]
                and _WEAPON_PRIMARY_TOTAL == _saved_w[3]
                and _WEAPON_PRIMARY_SEL == _saved_w[4]
                and _WEAPON_SECONDARY_BG == _saved_w[5]
                and _WEAPON_SECONDARY_CLIP == _saved_w[6]
                and _WEAPON_SECONDARY_TOTAL == _saved_w[7]
                and _WEAPON_SECONDARY_SEL == _saved_w[8]
            _same_crew = _CREW_NAME == _saved_crew_name
                and _CREW_REVIVE_BG == _saved_crew_bg
            _w_masked_after = _WEAPON_PRIMARY_BG:alpha() == 0
                and _WEAPON_PRIMARY_SEL:alpha() == 0
                and _WEAPON_SECONDARY_BG:alpha() == 0
                and _WEAPON_SECONDARY_SEL:alpha() == 0
            _crew_masked_after = _CREW_NAME:alpha() == 0
                and _CREW_REVIVE_BG:alpha() == 0
            _root_visible = P._root:visible()
            _p_verify = P:verify()
            _c_verify = C:_verify_render()
            _w_verify = W:verify()
            _writes_restored = _parent_writes
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._positive_group), "local_p_p must start acquired")
        self.assertTrue(bool(g._positive_w), "local_p_w must start acquired")
        self.assertTrue(bool(g._positive_crew), "crew_2 must start acquired")

        self.assertEqual(float(g._deepcopies), 0.0,
                         "read-only H5 pass must not deep-copy crew snapshots")
        self.assertEqual(float(g._writes_readonly), 0.0,
                         "read-only H5 pass must not write parent setters")

        self.assertTrue(bool(g._local_released), "player failure must release local_p_p")
        self.assertTrue(bool(g._w_same), "weapons group state must be retained")
        self.assertTrue(bool(g._crew_same), "crew group state must be retained")
        self.assertTrue(bool(g._w_masked), "weapons leaves must stay alpha 0")
        self.assertTrue(bool(g._crew_masked), "crew leaves must stay alpha 0")
        self.assertTrue(bool(g._uniques), "unrelated native leaves must keep their alpha")
        self.assertEqual(float(g._writes_failed), 0.0,
                         "local failure must not write parent setters")

        self.assertTrue(bool(g._local_back), "local_p_p must be re-acquired")
        self.assertTrue(bool(g._w_same_after), "weapons group state must stay unchanged")
        self.assertTrue(bool(g._crew_same_after), "crew group state must stay unchanged")
        self.assertTrue(bool(g._same_w), "weapons recovery must reuse the same leaves")
        self.assertTrue(bool(g._same_crew), "crew recovery must reuse the same leaves")
        self.assertTrue(bool(g._w_masked_after), "weapons leaves must remain alpha 0")
        self.assertTrue(bool(g._crew_masked_after), "crew leaves must remain alpha 0")
        self.assertTrue(bool(g._root_visible), "local root must be visible after repair")
        self.assertTrue(bool(g._p_verify), "player verifier must recover")
        self.assertTrue(bool(g._c_verify), "crew verifier must stay positive")
        self.assertTrue(bool(g._w_verify), "weapons verifier must stay positive")
        self.assertEqual(float(g._writes_restored), 0.0,
                         "local recovery must not write parent setters")


    def test_remote_teammate_interaction_leaf_hides_and_releases_crew(self):
        """Remote teammate interaction hides crew, then releases and recovers it.

        A distant ally entry panel is placed at the crew band with an active
        interact_panel (visible, alpha > 0) so _apply_native_priority hides the
        owned crew root and H5 releases crew_2, restoring the native crew
        alphas. The interaction is then ended through the genuine
        HUDManager:teammate_progress channel installed by the wrapping fixture,
        which hides the native leaf. Bounded updates must show the crew root
        again, certify its receipt, re-acquire the same crew native leaves at
        alpha 0, and leave the local player and weapons groups untouched. No
        parent setters and no crew snapshot deep copies are allowed.
        """
        lua = _local_runtime()
        lua.execute(r'''
            _positive_group = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _positive_crew = R._h5_groups and R._h5_groups["crew_2"] ~= nil
            _positive_p = P:verify()
            _positive_c = C:_verify_render()
            _positive_w = W:verify()

            _crew_root_before = C._root
            _local_p_state = R._h5_groups and R._h5_groups["local_p_p"] or nil
            _local_w_state = R._h5_groups and R._h5_groups["local_p_w"] or nil
            _local_label_before = P._h5_id_label
            _saved_crew_name, _saved_crew_amount = _CREW_NAME, _CREW_REVIVE_AMOUNT
            _saved_crew_arrow, _saved_crew_bg = _CREW_REVIVE_ARROW, _CREW_REVIVE_BG
            _saved_local_name = _LOCAL_NAME
            _saved_local_rbg, _saved_local_rh = _LOCAL_RADIAL_BG, _LOCAL_RADIAL_HEALTH
            _saved_local_rs = _LOCAL_RADIAL_SHIELD
            _saved_local_rev_bg = _LOCAL_REVIVE_BG
            _saved_local_rev_amt = _LOCAL_REVIVE_AMOUNT
            _saved_local_rev_arrow = _LOCAL_REVIVE_ARROW

            local crew_x, crew_y = C._root:x(), C._root:y()
            local crew_w, crew_h = C._root:w(), C._root:h()

            _REMOTE = panel_double:panel({name = "remote_interaction_entry"})
            _REMOTE:set_shape(crew_x, crew_y, crew_w, crew_h)
            _REMOTE:set_visible(true)
            _REMOTE_PLAYER = _REMOTE:panel({name = "player"})
            _REMOTE_PLAYER:set_shape(0, 0, crew_w, crew_h)
            _REMOTE_PLAYER:set_visible(true)
            _REMOTE_INTERACT = _REMOTE_PLAYER:text({
                name = "interact_panel", text = "Revive",
                font = "fonts/font_medium_mf",
            })
            _REMOTE_INTERACT:set_shape(10, 10, 120, 30)
            _REMOTE_INTERACT:set_alpha(.7)
            _REMOTE_INTERACT:set_visible(true)
            _G._remote_progress_leaf = _REMOTE_INTERACT
            mgr._teammate_panels[3] = {
                _peer_id = 3, _ai = false, _panel = _REMOTE,
                _special_equipment = {},
            }

            _progress_before = _G._teammate_progress_calls or 0
            mgr:teammate_progress(3, 1, true, "revive", 10, nil)
            _progress_started = (_G._teammate_progress_calls or 0)
                == _progress_before + 1
            _interact_active = _REMOTE_INTERACT:visible() == true

            _remote_writes = 0
            local function spy_remote(parent)
                for _, method_name in ipairs({"set_alpha", "set_visible",
                    "set_shape", "clear", "remove", "set_parent"}) do
                    local original = parent[method_name]
                    if type(original) == "function" then
                        parent[method_name] = function(self, ...)
                            _remote_writes = _remote_writes + 1
                            return original(self, ...)
                        end
                    end
                end
            end
            spy_remote(_REMOTE)
            spy_remote(_REMOTE_PLAYER)

            _parent_writes = 0
            R:update(mgr, 1.2, .1)
            R:update(mgr, 1.3, .1)

            _crew_hidden = not C._root:visible()
            _crew_group_released = (R._h5_groups == nil)
                or (R._h5_groups["crew_2"] == nil)
            _crew_name_restored = _CREW_NAME:alpha() == .7
            _crew_amount_restored = _CREW_REVIVE_AMOUNT:alpha() == .7
            _crew_arrow_restored = _CREW_REVIVE_ARROW:alpha() == .7
            _crew_bg_restored = _CREW_REVIVE_BG:alpha() == .7
            _local_p_same = R._h5_groups
                and R._h5_groups["local_p_p"] == _local_p_state
            _local_w_same = R._h5_groups
                and R._h5_groups["local_p_w"] == _local_w_state
            _local_root_visible_during = P._root:visible()
            _weapons_root_visible_during = W._root:visible()
            _player_verify_during = P:verify()
            _weapons_verify_during = W:verify()
            _writes_hidden = _parent_writes
            _remote_writes_hidden = _remote_writes

            _parent_writes = 0
            _remote_writes = 0
            _progress_before = _G._teammate_progress_calls or 0
            mgr:teammate_progress(3, 1, false, "revive", 0, true)
            _progress_ended = (_G._teammate_progress_calls or 0)
                == _progress_before + 1
            _interact_hidden = _REMOTE_INTERACT:visible() == false
            R:update(mgr, 1.4, .1)
            R:update(mgr, 1.5, .1)

            local receipt = C:update(mgr, 1.6, .1)
            _crew_receipt_ok = type(receipt) == "table"
                and receipt.ok == true and receipt.module == C
                and receipt.root == C._root and receipt.manager == C._manager
                and receipt.verifier == C._verify_render
                and C._root:visible() == true and C._root:alpha() == 1

            _crew_visible = C._root:visible()
            _crew_verify = C:_verify_render()
            _crew_group_back = R._h5_groups
                and R._h5_groups["crew_2"] ~= nil
            _crew_root_same = C._root == _crew_root_before
            _same_crew = (_CREW_NAME == _saved_crew_name)
                and (_CREW_REVIVE_AMOUNT == _saved_crew_amount)
                and (_CREW_REVIVE_ARROW == _saved_crew_arrow)
                and (_CREW_REVIVE_BG == _saved_crew_bg)
            _crew_masked = _CREW_NAME:alpha() == 0
                and _CREW_REVIVE_AMOUNT:alpha() == 0
                and _CREW_REVIVE_ARROW:alpha() == 0
                and _CREW_REVIVE_BG:alpha() == 0

            _local_p_back_same = R._h5_groups
                and R._h5_groups["local_p_p"] == _local_p_state
            _local_w_back_same = R._h5_groups
                and R._h5_groups["local_p_w"] == _local_w_state
            _local_root_visible = P._root:visible()
            _weapons_root_visible = W._root:visible()
            _player_verify = P:verify()
            _crew_verify_after = C:_verify_render()
            _weapons_verify = W:verify()
            _identity_same = P._h5_id_label == _local_label_before
                and P._h5_identity_verified == true
            _same_local_leaves = (_LOCAL_NAME == _saved_local_name)
                and (_LOCAL_RADIAL_BG == _saved_local_rbg)
                and (_LOCAL_RADIAL_HEALTH == _saved_local_rh)
                and (_LOCAL_RADIAL_SHIELD == _saved_local_rs)
                and (_LOCAL_REVIVE_BG == _saved_local_rev_bg)
                and (_LOCAL_REVIVE_AMOUNT == _saved_local_rev_amt)
                and (_LOCAL_REVIVE_ARROW == _saved_local_rev_arrow)
            _local_masked = _LOCAL_NAME:alpha() == 0
                and _LOCAL_RADIAL_BG:alpha() == 0
                and _LOCAL_RADIAL_HEALTH:alpha() == 0
                and _LOCAL_RADIAL_SHIELD:alpha() == 0
                and _LOCAL_REVIVE_BG:alpha() == 0
                and _LOCAL_REVIVE_AMOUNT:alpha() == 0
                and _LOCAL_REVIVE_ARROW:alpha() == 0
            _writes_recovery = _parent_writes
            _remote_writes_recovery = _remote_writes

            local original_snapshot = ACT.get_crew_snapshot
            _snapshot_calls = 0
            ACT.get_crew_snapshot = function(self, ...)
                _snapshot_calls = _snapshot_calls + 1
                return original_snapshot(self, ...)
            end
            R:_coordinate_h5_native_duplicates()
            ACT.get_crew_snapshot = original_snapshot
            _deepcopies = _snapshot_calls
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._positive_group), "local_p_p must start acquired")
        self.assertTrue(bool(g._positive_crew), "crew_2 must start acquired")
        self.assertTrue(bool(g._positive_p), "player verifier must start positive")
        self.assertTrue(bool(g._positive_c), "crew verifier must start positive")
        self.assertTrue(bool(g._positive_w), "weapons verifier must start positive")
        self.assertTrue(bool(g._progress_started),
                        "the genuine interaction start must reach the native channel")
        self.assertTrue(bool(g._interact_active),
                        "the remote interaction leaf must start visible")

        self.assertTrue(bool(g._crew_hidden),
                        "remote interaction must hide the owned crew root")
        self.assertTrue(bool(g._crew_group_released),
                        "H5 must release crew_2 while the crew root is hidden")
        self.assertTrue(bool(g._crew_name_restored),
                        "native crew name alpha must be restored")
        self.assertTrue(bool(g._crew_amount_restored),
                        "native crew revive amount alpha must be restored")
        self.assertTrue(bool(g._crew_arrow_restored),
                        "native crew revive arrow alpha must be restored")
        self.assertTrue(bool(g._crew_bg_restored),
                        "native crew revive background alpha must be restored")
        self.assertTrue(bool(g._local_p_same),
                        "local player group state must survive the crew hide")
        self.assertTrue(bool(g._local_w_same),
                        "local weapons group state must survive the crew hide")
        self.assertTrue(bool(g._local_root_visible_during),
                        "local player root must stay visible during the crew hide")
        self.assertTrue(bool(g._weapons_root_visible_during),
                        "local weapons root must stay visible during the crew hide")
        self.assertTrue(bool(g._player_verify_during),
                        "player verifier must stay positive during the crew hide")
        self.assertTrue(bool(g._weapons_verify_during),
                        "weapons verifier must stay positive during the crew hide")
        self.assertEqual(float(g._writes_hidden), 0.0,
                         "the crew hide must not write parent setters")
        self.assertEqual(float(g._remote_writes_hidden), 0.0,
                         "the crew hide must not write remote parent setters")

        self.assertTrue(bool(g._progress_ended),
                        "the genuine interaction end must reach the native channel")
        self.assertTrue(bool(g._interact_hidden),
                        "the genuine interaction end must hide the native leaf")
        self.assertTrue(bool(g._crew_visible),
                        "crew root must be visible after the interaction ends")
        self.assertTrue(bool(g._crew_verify),
                        "crew render must recertify after the interaction ends")
        self.assertTrue(bool(g._crew_receipt_ok),
                        "the crew receipt must be valid for H5 re-acquisition")
        self.assertTrue(bool(g._crew_group_back),
                        "H5 must re-acquire crew_2 after the interaction ends")
        self.assertTrue(bool(g._crew_root_same),
                        "crew root identity must be preserved")
        self.assertTrue(bool(g._same_crew),
                        "crew recovery must reuse the same native leaves")
        self.assertTrue(bool(g._crew_masked),
                        "recovered crew native leaves must return to alpha 0")

        self.assertTrue(bool(g._local_p_back_same),
                        "local player group state must stay unchanged")
        self.assertTrue(bool(g._local_w_back_same),
                        "local weapons group state must stay unchanged")
        self.assertTrue(bool(g._local_root_visible),
                        "local player root must remain visible after recovery")
        self.assertTrue(bool(g._weapons_root_visible),
                        "local weapons root must remain visible after recovery")
        self.assertTrue(bool(g._player_verify),
                        "player verifier must stay positive after recovery")
        self.assertTrue(bool(g._crew_verify_after),
                        "crew verifier must stay positive after recovery")
        self.assertTrue(bool(g._weapons_verify),
                        "weapons verifier must stay positive after recovery")
        self.assertTrue(bool(g._identity_same),
                        "owned local identity must stay certified")
        self.assertTrue(bool(g._same_local_leaves),
                        "local recovery must reuse the same native leaves")
        self.assertTrue(bool(g._local_masked),
                        "local native leaves must remain at alpha 0")
        self.assertEqual(float(g._writes_recovery), 0.0,
                         "recovery must not write parent setters")
        self.assertEqual(float(g._remote_writes_recovery), 0.0,
                         "recovery must not write remote parent setters")
        self.assertEqual(float(g._deepcopies), 0.0,
                         "the H5 pass must not deep-copy crew snapshots")

    def test_local_unit_loss_releases_radial_and_reconciliation_recovers(self):
        """Custody-like local unit loss releases radials and reconcile restores them.

        The genuine player update path (P.update -> P:_capture_and_render ->
        ACT:refresh) observes no local unit and no character_damage, so the
        local actor snapshot loses valid health/armor. H5 then releases the
        native radial leaves while keeping the owned identity group, and the
        local roots stay visible. Declaring the unit back before the next state
        and running bounded updates must re-acquire the exact same radial
        primitives at alpha 0, keep the owned roots visible and recertify the
        same identity label. No parent setters and no crew deep copies.
        """
        lua = _local_runtime()
        lua.execute(r'''
            _positive_group = R._h5_groups and R._h5_groups["local_p_p"] ~= nil
            _positive_label = P._h5_id_label ~= nil
                and P._h5_identity_verified == true
            _positive_p = P:verify()
            _positive_c = C:_verify_render()
            _positive_w = W:verify()

            _root_before, _w_root_before, _c_root_before = P._root, W._root, C._root
            _label_before = P._h5_id_label
            _saved_rbg, _saved_rh = _LOCAL_RADIAL_BG, _LOCAL_RADIAL_HEALTH
            _saved_rs = _LOCAL_RADIAL_SHIELD
            _saved_rev_bg = _LOCAL_REVIVE_BG
            _saved_rev_amt = _LOCAL_REVIVE_AMOUNT
            _saved_rev_arrow = _LOCAL_REVIVE_ARROW

            local original_player_unit = managers.player.player_unit
            managers.player.player_unit = function(self) return nil end

            _parent_writes = 0
            R:update(mgr, 1.2, .1)
            R:update(mgr, 1.3, .1)

            local snap = ACT:get_actor(_SLOT)
            _actor_loss = snap == nil or snap.health == nil
                or snap.health.valid ~= true or snap.armor == nil
                or snap.armor.valid ~= true
            _radial_released = _LOCAL_RADIAL_BG:alpha() == .7
                and _LOCAL_RADIAL_HEALTH:alpha() == .7
                and _LOCAL_RADIAL_SHIELD:alpha() == .7
            _group_still = R._h5_groups
                and R._h5_groups["local_p_p"] ~= nil
            _identity_during = P._h5_id_label == _label_before
                and P._h5_identity_verified == true
            _local_root_visible_custody = P._root:visible()
            _weapons_root_visible_custody = W._root:visible()
            _crew_root_visible_custody = C._root:visible()
            _player_verify_custody = P:verify()
            _weapons_verify_custody = W:verify()
            _crew_verify_custody = C:_verify_render()
            _writes_custody = _parent_writes

            managers.player.player_unit = original_player_unit
            _parent_writes = 0
            R:update(mgr, 1.4, .1)
            R:update(mgr, 1.5, .1)

            _radial_back = _LOCAL_RADIAL_BG:alpha() == 0
                and _LOCAL_RADIAL_HEALTH:alpha() == 0
                and _LOCAL_RADIAL_SHIELD:alpha() == 0
            _same_radial = (_LOCAL_RADIAL_BG == _saved_rbg)
                and (_LOCAL_RADIAL_HEALTH == _saved_rh)
                and (_LOCAL_RADIAL_SHIELD == _saved_rs)
            _group_back = R._h5_groups
                and R._h5_groups["local_p_p"] ~= nil
            _root_same = P._root == _root_before
                and W._root == _w_root_before and C._root == _c_root_before
            _root_visible = P._root:visible()
            _weapons_root_visible = W._root:visible()
            _crew_root_visible = C._root:visible()
            _player_verify = P:verify()
            _weapons_verify = W:verify()
            _crew_verify = C:_verify_render()
            _same_label = P._h5_id_label == _label_before
            _identity_recert = P._h5_identity_verified == true
            _same_revive = (_LOCAL_REVIVE_BG == _saved_rev_bg)
                and (_LOCAL_REVIVE_AMOUNT == _saved_rev_amt)
                and (_LOCAL_REVIVE_ARROW == _saved_rev_arrow)
            _writes_recovery = _parent_writes

            local original_snapshot = ACT.get_crew_snapshot
            _snapshot_calls = 0
            ACT.get_crew_snapshot = function(self, ...)
                _snapshot_calls = _snapshot_calls + 1
                return original_snapshot(self, ...)
            end
            R:_coordinate_h5_native_duplicates()
            ACT.get_crew_snapshot = original_snapshot
            _deepcopies = _snapshot_calls
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._positive_group), "local_p_p must start acquired")
        self.assertTrue(bool(g._positive_label), "identity must start qualified")
        self.assertTrue(bool(g._positive_p), "player verifier must start positive")
        self.assertTrue(bool(g._positive_c), "crew verifier must start positive")
        self.assertTrue(bool(g._positive_w), "weapons verifier must start positive")

        self.assertTrue(bool(g._actor_loss),
                        "the genuine unit loss must invalidate local health/armor")
        self.assertTrue(bool(g._radial_released),
                        "H5 must release the radial natives during custody")
        self.assertTrue(bool(g._group_still),
                        "the certified local identity group must survive custody")
        self.assertTrue(bool(g._identity_during),
                        "the owned identity must stay certified during custody")
        self.assertTrue(bool(g._local_root_visible_custody),
                        "local player root must stay visible during custody")
        self.assertTrue(bool(g._weapons_root_visible_custody),
                        "local weapons root must stay visible during custody")
        self.assertTrue(bool(g._crew_root_visible_custody),
                        "crew root must stay visible during local custody")
        self.assertTrue(bool(g._player_verify_custody),
                        "player verifier must stay positive during custody")
        self.assertTrue(bool(g._weapons_verify_custody),
                        "weapons verifier must stay positive during custody")
        self.assertTrue(bool(g._crew_verify_custody),
                        "crew verifier must stay positive during custody")
        self.assertEqual(float(g._writes_custody), 0.0,
                         "custody release must not write parent setters")

        self.assertTrue(bool(g._radial_back),
                        "reconciliation must re-acquire the radial natives")
        self.assertTrue(bool(g._same_radial),
                        "reconciliation must reuse the same radial primitives")
        self.assertTrue(bool(g._group_back),
                        "local_p_p must remain acquired after reconciliation")
        self.assertTrue(bool(g._root_same),
                        "owned roots must keep their identity after reconciliation")
        self.assertTrue(bool(g._root_visible),
                        "local player root must be visible after reconciliation")
        self.assertTrue(bool(g._weapons_root_visible),
                        "local weapons root must be visible after reconciliation")
        self.assertTrue(bool(g._crew_root_visible),
                        "crew root must be visible after reconciliation")
        self.assertTrue(bool(g._player_verify),
                        "player verifier must recover after reconciliation")
        self.assertTrue(bool(g._weapons_verify),
                        "weapons verifier must recover after reconciliation")
        self.assertTrue(bool(g._crew_verify),
                        "crew verifier must recover after reconciliation")
        self.assertTrue(bool(g._same_label),
                        "reconciliation must reuse the same identity label")
        self.assertTrue(bool(g._identity_recert),
                        "the owned identity must be certified again")
        self.assertTrue(bool(g._same_revive),
                        "revive primitives must keep their identity")
        self.assertEqual(float(g._writes_recovery), 0.0,
                         "reconciliation must not write parent setters")
        self.assertEqual(float(g._deepcopies), 0.0,
                         "the H5 pass must not deep-copy crew snapshots")


if __name__ == "__main__":
    unittest.main()
