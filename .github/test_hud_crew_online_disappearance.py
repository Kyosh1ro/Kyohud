"""Online crew disappearance -- full session, real draw and real callbacks.

Scope: reproduce the in-engine symptom where the native teammate HUD stays
visible at the bottom while KyoHUD crew cards vanish, although the KyoHUD
player HUD remains. Real production chunks run through lupa/luajit21: the
full crew stack, actors.lua in both real contexts, the real KH:draw, the real
buff cell/progress producers, and the genuine registered HUDManager/PlayerManager
callbacks.

Session model: local peer 1; remote human peer 2 (panel 2, ai=false); bots at
panels 1 and 3 (ai=true); criminals records taken with live shaped units. PM
ammo publications use set_synced_ammo_info(2,1,...) and (2,2,...), deployable
uses the peer object, cable ties and grenade use peer ids. HUDManager health,
armor, revives and condition events are dispatched through the actual
installed PostHooks only after the native teammate panels are complete (the
documented revives trap). Native leaves mirror online_runtime: both weapon
panels with their leaves and nested selection bitmap, deployable, cable ties,
revive panel, plus a unique grenades_radial that must never be touched.

Sustained R:update runs from t=0 to 2.0 with dt <= 0.01, covering the 0.5 s
polls and 0.05 s presentations, with a downed/reanimation condition event in
flight. Buffs sit at the configured default position and the real producers
create frames/outlines that must yield above the crew band without moving the
crew. KH_InitHUD (the real init_finalize PostHook) then runs after the first
stabilized presentation and the crew must become visible and certified again.
Native H5 coverage rows/leaves, untouched unique leaf alpha, zero native
parent alpha writes, and the no-deepcopy read-only H5 pass are all asserted.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_crew import ROOT
from test_hud_crew_online_ammo import _crew_lua, RENDER_SETUP, ACTORS_PATH


EXTRA_SETUP = r'''
    Network = Network or {is_server = function() return true end}
    tweak_data = tweak_data or {}
    tweak_data.equipments = tweak_data.equipments or {}
    tweak_data.equipments.ammo_bag = {
        text_id = "ammo_bag_name",
        icon = "equipment_ammo_bag",
    }
    tweak_data.blackmarket = tweak_data.blackmarket or {}
    tweak_data.blackmarket.projectiles = tweak_data.blackmarket.projectiles or {}
    tweak_data.blackmarket.projectiles.smoke_screen_grenade = {
        ability = true,
        name_id = "ability_smoke",
        icon = "smoke_screen_grenade",
    }
    tweak_data.menu = tweak_data.menu or {}
    tweak_data.menu.pd2_small_font = "fonts/font_small_mf"

    function HUDManager:set_teammate_health(i, data)
        if not self._teammate_panels[i] then
            self._teammate_panels[i] = {}
        end
        self._teammate_panels[i]._health_data = data
    end

    function HUDManager:set_teammate_armor(i, data)
        if not self._teammate_panels[i] then
            self._teammate_panels[i] = {}
        end
        self._teammate_panels[i]._armor_data = data
    end

    function HUDManager:set_teammate_revives(i, amount)
        if not self._teammate_panels[i] then
            self._teammate_panels[i] = {}
        end
        self._teammate_panels[i].revives = amount
    end

    function HUDManager:set_teammate_condition(i, icon, text)
        if not self._teammate_panels[i] then
            self._teammate_panels[i] = {}
        end
        self._teammate_panels[i].condition_icon = icon
        self._teammate_panels[i].condition_text = text
    end

    function PlayerManager:set_synced_deployable_equipment(peer, deployable, amount)
        if type(peer) ~= "table" then return end
        local peer_id = peer:id()
        if type(peer_id) ~= "number" then return end
        self._global.synced_deployables[peer_id] = {
            deployable = deployable,
            amount = amount,
        }
    end

    function PlayerManager:set_synced_cable_ties(peer_id, amount)
        if type(peer_id) ~= "number" then return end
        self._global.synced_cable_ties[peer_id] = {amount = amount}
    end

    function PlayerManager:set_synced_grenades(peer_id, grenade, amount)
        if type(peer_id) ~= "number" then return end
        self._global.synced_grenades[peer_id] = {
            grenade = grenade,
            amount = amount,
        }
    end
'''

RESET_HOOKS = r'''
    kyohud.hud._installed_hooks.KyohHUD_Actors_Health = nil
    kyohud.hud._installed_hooks.KyohHUD_Actors_Armor = nil
    kyohud.hud._installed_hooks.KyohHUD_Actors_Revives = nil
    kyohud.hud._installed_hooks.KyohHUD_Actors_Condition = nil
'''

CORE_SETUP = r'''
    dofile = function() end
    TimerManager = {game = function() return {time = function() return 1 end} end}

    local mt = getmetatable(panel_double).__index
    if type(mt.polyline) ~= "function" then
        mt.polyline = function(self, cfg)
            local p = self:polygon(cfg)
            p._points = cfg.points
            p._line_width = cfg.line_width
            return p
        end
    end
    if type(mt.gradient) ~= "function" then
        mt.gradient = function(self, cfg)
            local p = self:polygon(cfg)
            p._gradient_points = cfg.gradient_points
            p._orientation = cfg.orientation
            return p
        end
    end

    local source_color = Color
    local color_mt = {__index = {
        with_alpha = function(self, a)
            return setmetatable({r = self.r, g = self.g, b = self.b, a = a}, color_mt)
        end,
    }}
    local function make_color(...)
        return setmetatable(source_color(...), color_mt)
    end
    Color = setmetatable({
        white = make_color(1, 1, 1),
        black = make_color(0, 0, 0),
    }, {__call = function(_, ...) return make_color(...) end})
'''

SESSION_SETUP = r'''
    kyohud.settings.enable_hud_foundation = true
    kyohud.settings.enable_crew = true
    kyohud.settings.hud_scale = 1.0
    kyohud.settings.enable_player = false
    kyohud.settings.enable_weapons = false
    kyohud.settings.enable_equipment = false
    kyohud.settings.enable_buffs = true
    kyohud.settings.buff_position_x = 50
    kyohud.settings.buff_position_y = 98
    kyohud.settings.icon_size = 32
    kyohud.settings.opacity = 0.9
    _G.panel_double:set_shape(0, 0, __W__, __H__)

    A = kyohud.hud.actors
    R = kyohud.hud.runtime
    C = kyohud.hud.crew

    local function bot_unit(ratio)
        return {
            _alive = true,
            character_damage = function(self)
                return {
                    dead = function() return false end,
                    fatal = function() return false end,
                    bleed_out = function() return false end,
                    arrested = function() return nil end,
                    health_ratio = function() return ratio end,
                }
            end,
            inventory = function(self) return _G._inventory end,
        }
    end

    for _, rec in ipairs(managers.criminals:characters()) do
        local panel_id = rec.data and rec.data.panel_id
        if panel_id == 1 then
            rec.unit = bot_unit(0.7)
        elseif panel_id == 3 then
            rec.unit = bot_unit(0.8)
        end
    end

    _G._remote_peer = managers.network:session():peer(2)
    A:refresh_crew(managers.hud, 0)

    managers.player:set_synced_ammo_info(2, 1, 30, 7, 67, 120)
    managers.player:set_synced_ammo_info(2, 2, 40, 12, 95, 160)
    managers.player:set_synced_deployable_equipment(_G._remote_peer, "ammo_bag", 2)
    managers.player:set_synced_cable_ties(2, 1)
    managers.player:set_synced_grenades(2, "smoke_screen_grenade", 1)

    R:mount(managers.hud)
    _setup_ok = C._mounted == true and C._layout_cache ~= nil and C._root ~= nil
    if not _setup_ok then return end

    targets = {}
    covered_targets = {}
    parents = {}
    uniques = {}
    local lc = C._layout_cache

    local function add_leaves(parent, names, cover)
        for _, name in ipairs(names) do
            local leaf = parent:bitmap({name = name})
            leaf:set_shape(0, 0, 10, 10)
            leaf:set_alpha(0.7)
            targets[#targets + 1] = leaf
            if cover then
                covered_targets[#covered_targets + 1] = leaf
            end
        end
    end

    for slot = 1, 3 do
        local entry = managers.hud._teammate_panels[slot]
        local ep = panel_double:panel({name = "native_crew_" .. slot})
        ep:set_shape(
            lc.x + (slot - 1) * (lc.card_w + lc.gap),
            lc.y - (lc.state_h or 0),
            lc.card_w,
            lc.card_h + (lc.state_h or 0))
        entry._panel = ep
        parents[#parents + 1] = ep

        local player = ep:panel({name = "player"})
        player:set_shape(0, 0, ep:w(), ep:h())
        parents[#parents + 1] = player

        local cover = slot == 2
        local weapons = player:panel({name = "weapons_panel"})
        weapons:set_shape(0, 0, ep:w(), 40)
        parents[#parents + 1] = weapons

        local weapon_names = {"secondary_weapon_panel", "primary_weapon_panel"}
        for index, name in ipairs(weapon_names) do
            local weapon = weapons:panel({name = name})
            weapon:set_shape((index - 1) * ep:w() * 0.5, 0, ep:w() * 0.5, 40)
            parents[#parents + 1] = weapon
            add_leaves(weapon, {"bg", "ammo_clip", "ammo_total"}, cover)
            local selection = weapon:panel({name = "weapon_selection"})
            selection:set_shape(0, 0, 10, 10)
            parents[#parents + 1] = selection
            add_leaves(selection, {"weapon_selection"}, cover)
        end

        local deployable = player:panel({name = "deployable_equipment_panel"})
        deployable:set_shape(0, 50, 60, 24)
        parents[#parents + 1] = deployable
        add_leaves(deployable, {"bg", "equipment", "amount"}, cover)

        local ties = player:panel({name = "cable_ties_panel"})
        ties:set_shape(0, 76, 60, 24)
        parents[#parents + 1] = ties
        add_leaves(ties, {"bg", "cable_ties", "amount"}, cover)

        local revive = player:panel({name = "revive_panel"})
        revive:set_shape(0, 20, 60, 24)
        parents[#parents + 1] = revive
        add_leaves(revive, {"revive_bg", "revive_amount", "revive_arrow"}, cover)

        local unique = player:bitmap({name = "grenades_radial"})
        unique:set_shape(ep:w() - 40, 8, 10, 10)
        unique:set_alpha(0.6)
        uniques[#uniques + 1] = unique
    end

    _parent_writes = 0
    for _, p in ipairs(parents) do
        local set = p.set_alpha
        p.set_alpha = function(self, v)
            _parent_writes = _parent_writes + 1
            return set(self, v)
        end
    end

    managers.hud:set_teammate_health(2, {current = 82, total = 100})
    managers.hud:set_teammate_armor(2, {current = 45, total = 100})
    managers.hud:set_teammate_revives(2, 4)
    managers.hud:set_teammate_condition(2, "mugshot_normal", "")
'''

BUFF_SETUP = r'''
    kyohud.settings.enable_buffs = true
    kyohud.settings.buff_position_x = 50
    kyohud.settings.buff_position_y = 98
    kyohud.settings.enable_killfeed = false
    kyohud.settings.enable_kill_score = false
    kyohud.settings.enable_kill_medals = false
    kyohud._gameinfo_bridge_active = true

    kyohud.is_buff_visible = function(_, id) return id == "test" end
    kyohud._buffs.test = {
        id = "test",
        icon = {texture = "guis/textures/pd2/hud_timer"},
        color = Color.white,
        start_t = 0,
        duration = 30,
        t_end = 30,
    }

    local real_frame = kyohud.DrawBuffCellFrame
    local real_progress = kyohud.DrawTimedBuffProgress
    _buff_frame_y = nil
    _buff_progress_y = nil
    _progress_calls = 0
    kyohud.DrawBuffCellFrame = function(panel, x, y, w, h, ...)
        _buff_frame_y = y + h * 0.5
        return real_frame(panel, x, y, w, h, ...)
    end
    kyohud.DrawTimedBuffProgress = function(panel, x, y, w, h, ...)
        _buff_progress_y = y + h * 0.5
        _progress_calls = _progress_calls + 1
        return real_progress(panel, x, y, w, h, ...)
    end

    local parent = C._parent_panel
    local default_layout = kyohud.compute_buff_row_layout(
        1, 50, 98, parent:w(), parent:h(), 32, 5.12, 2.56, 18)
    _default_y = default_layout.positions[1].y
    kyohud:ensure_panel(true)
    kyohud:draw()
'''

RUN_LOOP = r'''
    for i = 0, 200 do
        local t = i * 0.01
        if i == 80 then
            managers.hud:set_teammate_condition(2, "mugshot_downed", "REANIMATING")
        end
        if i == 130 then
            managers.hud:set_teammate_condition(2, "mugshot_normal", "")
        end
        if i % 5 == 0 then
            kyohud:draw()
        end
        R:update(managers.hud, t, 0.01)
    end

    _stable_root_visible = C._root:visible() == true
    _stable_verified = C:_verify_render() == true
    _stable_positions = C._expected_positions ~= nil
    if _stable_positions then
        for pos = 1, 3 do
            if C._expected_positions[pos] == true then
                local card = C._cards[pos]
                if not (card and card.root and card.root:visible() == true) then
                    _stable_positions = false
                end
            end
        end
    end

    local receipt = C:update(managers.hud, 2.1, 0.05)
    _receipt_ok = type(receipt) == "table" and receipt.ok == true
        and receipt.module == C and receipt.root == C._root

    _native_coverage_ok = C._native_coverage ~= nil
    if _native_coverage_ok then
        local snap = A:get_crew_snapshot()
        for pos = 1, 3 do
            local row = C._native_coverage[pos]
            local entry = nil
            for _, candidate in ipairs(snap) do
                if candidate.position == pos then
                    entry = candidate
                end
            end
            if not (row and row.valid == true and entry
                and row.occupant_token == entry.occupant_token
                and row.slot == entry.slot) then
                _native_coverage_ok = false
            end
        end
    end

    _covered_leaves = true
    for _, leaf in ipairs(covered_targets) do
        local ok, alpha = pcall(function() return leaf:alpha() end)
        if not ok or alpha ~= 0 then
            _covered_leaves = false
        end
    end

    _unique_ok = true
    for _, leaf in ipairs(uniques) do
        local ok, alpha = pcall(function() return leaf:alpha() end)
        if not ok or alpha ~= 0.6 then
            _unique_ok = false
        end
    end

    _parent_writes_ok = _parent_writes == 0
    _buff_yielded = _buff_frame_y ~= nil and _default_y ~= nil
        and _buff_frame_y < _default_y - 0.01
    _progress_seen = _progress_calls > 0

    local lc = C._layout_cache
    _crew_fixed = lc ~= nil and C._root ~= nil and C._root:visible() == true
        and math.abs(C._root:x() - lc.x) < 0.01
        and math.abs(C._root:y() - (lc.y - (lc.state_h or 0))) < 0.01
        and math.abs(C._root:w() - lc.total_w) < 0.01
        and math.abs(C._root:h() - (lc.card_h + (lc.state_h or 0))) < 0.01

    local original_get = A.get_crew_snapshot
    _copies = 0
    A.get_crew_snapshot = function(self)
        _copies = _copies + 1
        return original_get(self)
    end
    for _ = 1, 10 do
        R:_coordinate_h5_native_duplicates(receipt)
    end
    A.get_crew_snapshot = original_get

    managers.hud:init_finalize()
    _init_called = true

    kyohud.settings.enable_buffs = true
    kyohud.settings.buff_position_x = 50
    kyohud.settings.buff_position_y = 98
    kyohud._gameinfo_bridge_active = true
    kyohud._buffs.test = {
        id = "test",
        icon = {texture = "guis/textures/pd2/hud_timer"},
        color = Color.white,
        start_t = 1,
        duration = 30,
        t_end = 31,
    }

    for i = 1, 100 do
        local t = 2.2 + i * 0.01
        if i % 5 == 0 then
            kyohud:draw()
        end
        R:update(managers.hud, t, 0.01)
    end

    _recover_visible = C._root:visible() == true
    _recover_verified = C:_verify_render() == true
    _recover_positions = C._expected_positions ~= nil
    if _recover_positions then
        for pos = 1, 3 do
            if C._expected_positions[pos] == true then
                local card = C._cards[pos]
                if not (card and card.root and card.root:visible() == true) then
                    _recover_positions = false
                end
            end
        end
    end
    _recover_buff_yielded = _buff_frame_y ~= nil and _default_y ~= nil
        and _buff_frame_y < _default_y - 0.01

    local recover_receipt = C:update(managers.hud, 3.5, 0.05)
    _recover_receipt_ok = type(recover_receipt) == "table"
        and recover_receipt.ok == true
        and recover_receipt.module == C
        and recover_receipt.root == C._root
'''


def _online_disappearance_runtime(width, height):
    lua, ok = _crew_lua()
    assert ok, "RED: lua/hud/crew.lua must exist"
    lua.execute(RENDER_SETUP)
    lua.execute(EXTRA_SETUP)
    lua.execute(RESET_HOOKS)
    actors_src = ACTORS_PATH.read_text(encoding="utf-8-sig")
    for context in ("lib/managers/playermanager", "lib/managers/hudmanagerpd2"):
        lua.globals().RequiredScript = context
        lua.execute(actors_src)
    lua.execute(CORE_SETUP)
    for relative in (
        "lua/ky_buff_presentation.lua",
        "lua/core.lua",
        "lua/ky_buff_render.lua",
        "lua/ky_killfeed_render.lua",
    ):
        lua.execute((ROOT / relative).read_text(encoding="utf-8-sig"))
    lua.execute(
        SESSION_SETUP.replace("__W__", str(width)).replace("__H__", str(height))
    )
    lua.execute(BUFF_SETUP)
    lua.execute(RUN_LOOP)
    return lua


class CrewOnlineDisappearanceTests(unittest.TestCase):

    def test_online_session_keeps_crew_visible_with_native_bottom_hud(self):
        """Full online session: crew survives native bottom panels and reset.

        Real crew/actors/runtime/core/buff chunks plus real callbacks run for
        an absent-from-fixtures 16:9 dimension (1280x720) and 1360x768. After
        stabilization the crew root must be visible and certified, every
        presented position must have a visible card root, the direct C:update
        receipt must be ok/module/root, native coverage rows must match the
        live occupants, covered native leaves must be alpha 0 (unique
        grenades_radial stays 0.6), native parent alpha writes must be zero,
        real buff frames must yield above the crew band without moving it,
        and the read-only H5 pass must not deep-copy public snapshots. The
        real KH_InitHUD/init_finalize callback then runs and sustained updates
        must restore the same visible, certified crew presentation.
        """
        for width, height in ((1280, 720), (1360, 768)):
            with self.subTest(width=width, height=height):
                lua = _online_disappearance_runtime(width, height)
                g = lua.globals()

                self.assertIs(g._setup_ok, True,
                    "session must mount the real crew root")
                self.assertIs(g._stable_root_visible, True,
                    "crew root must stay visible after sustained updates")
                self.assertIs(g._stable_verified, True,
                    "C:_verify_render() must certify the stabilized crew")
                self.assertIs(g._stable_positions, True,
                    "every presented position must keep a visible card root")
                self.assertIs(g._receipt_ok, True,
                    "C:update must return ok/module/root after stabilization")

                self.assertIs(g._native_coverage_ok, True,
                    "native coverage rows must match the presented occupants")
                self.assertIs(g._covered_leaves, True,
                    "every covered native leaf must be acquired at alpha 0")
                self.assertIs(g._unique_ok, True,
                    "the unique grenades_radial alpha must stay 0.6")
                self.assertIs(g._parent_writes_ok, True,
                    "native parent alpha setters must never be written")

                self.assertIs(g._buff_yielded, True,
                    "real buff frames must yield above the crew band")
                self.assertIs(g._progress_seen, True,
                    "real buff progress outlines must be produced")
                self.assertIs(g._crew_fixed, True,
                    "buff yielding must not move the crew root")

                self.assertEqual(int(g._copies), 0,
                    "the read-only H5 pass must not deep-copy crew snapshots")

                self.assertIs(g._init_called, True,
                    "the real KH_InitHUD/init_finalize callback must run")
                self.assertIs(g._recover_visible, True,
                    "crew root must be visible again after init_finalize")
                self.assertIs(g._recover_verified, True,
                    "crew must be certified again after init_finalize")
                self.assertIs(g._recover_positions, True,
                    "every presented position must recover its visible card")
                self.assertIs(g._recover_buff_yielded, True,
                    "buff yielding must keep working after init_finalize")
                self.assertIs(g._recover_receipt_ok, True,
                    "C:update must return ok/module/root after init_finalize")


if __name__ == "__main__":
    unittest.main()
