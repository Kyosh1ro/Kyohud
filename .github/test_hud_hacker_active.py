"""Lot 6 RED: local Hacker ACTIVE substitutes only the two native ability
bitmap leaves, after the real native activation action and registered event
hook, without any runtime update between activation and assertions.

Reuses the existing equipment/consumables fixture through
test_hud_native_cooldown_replacement._runtime(). The suite is expected to fail
on the current production: it does not acquire
radial_ability/ability_meter and radial_ability/ability_icon and does not
render the synchronous ACTIVE row.
"""
from pathlib import Path
import unittest

from test_hud_native_cooldown_replacement import _runtime

ROOT = Path(__file__).resolve().parents[1]
EQUIPMENT_PATH = ROOT / "lua" / "hud" / "equipment.lua"


def _read(path):
    assert path.is_file(), f"required production chunk missing: {path}"
    return path.read_text(encoding="utf-8-sig")


# Native constructor shape and the exact small native animation excerpts.
# The panel chain is added to the real teammate entry already built by _runtime.
HACKER_FIXTURE = r'''
HUDTeammate = HUDTeammate or {}
math.lerp = math.lerp or function(a, b, t) return a + (b - a) * t end

-- Exact excerpt: core/lib/utils/coreevent.lua:228-244
function over(seconds, f, fixed_dt)
    local t = 0
    while true do
        local dt = coroutine.yield()
        t = t + (fixed_dt and 0.03333333333333333 or dt)
        if seconds <= t then break end
        f(t / seconds, t)
    end
    f(1, seconds)
end

-- Exact excerpt: lib/managers/hud/hudteammate.lua:2087-2095
function HUDTeammate.activate_ability_radial_anim(o, anim_time, progress_start,
        radial_ability_panel, ability_meter, health_icon)
    radial_ability_panel:set_visible(true)
    over(anim_time, function(p)
        local progress = progress_start * math.lerp(1, 0, p)
        ability_meter:set_color(Color(1, progress, 1, 1))
    end)
    radial_ability_panel:set_visible(false)
end

-- Fixture-only Diesel animate/stop scaffolding. The exact anim above yields
-- before its first meter write, so the native meter color stays stale.
local Panel = getmetatable(panel_double)
function Panel:stop() self._ky_animation = nil end
function Panel:animate(fn, ...)
    local co = coroutine.create(fn)
    self._ky_animation = co
    local ok, err = coroutine.resume(co, self, ...)
    if not ok then error(err) end
end

local slot = HUDManager.PLAYER_PANEL
local entry = managers.hud._teammate_panels[slot]
local player = entry._panel:child("player")
local radial_health_panel = player:panel({name = "radial_health_panel"})
local radial_ability = radial_health_panel:panel({name = "radial_ability"})
local ability_meter = radial_ability:bitmap({
    name = "ability_meter", texture = "guis/textures/pd2/hud_fearless"})
local ability_icon = radial_ability:bitmap({name = "ability_icon"})
local sentinel = radial_health_panel:panel({name = "third_party_ability_sentinel"})

radial_health_panel:set_shape(0, 0, 1, 1)
radial_health_panel:set_visible(true)
radial_ability:set_shape(0, 0, 1, 1)
radial_ability:set_color(Color(1, 1, 1, 1))
radial_ability:set_alpha(.73)
radial_ability:set_visible(false)
ability_meter:set_shape(0, 0, 1, 1)
ability_meter:set_color(Color(1, 0, 1, 1))
ability_meter:set_alpha(.81)
ability_meter:set_visible(true)
ability_icon:set_shape(0, 0, 1, 1)
ability_icon:set_color(Color(1, 1, 1, 1))
ability_icon:set_alpha(.67)
ability_icon:set_visible(true)
sentinel:set_shape(2, 2, 8, 8)
sentinel:set_color(Color(1, .5, .5, 1))
sentinel:set_alpha(.55)
sentinel:set_visible(true)

entry._radial_health_panel = radial_health_panel
_G._ability_parent = radial_ability
_G._ability_meter = ability_meter
_G._ability_icon = ability_icon
_G._ability_sentinel = sentinel
_G._ability_health_parent = radial_health_panel

-- Stable native-looking local unit inventory identity.
managers.player.player_unit = function(self) return player_unit end
player_unit.inventory = function() return inventory end

-- Real pocket ECM source: 1 charge of 2, native icon, 100s base cooldown.
_game_clock:set_time(1000)
managers.player:_native_set_grenades("pocket_ecm_jammer", 1, 2)
_native_set_projectile_tweak("pocket_ecm_jammer", {
    ability = true, base_cooldown = 100,
    icon = "guis/dlcs/joy/textures/pd2/hud_pocket_ecm_jammer"})
managers.player:_native_set_replenish_timer(1017)

-- Native-shaped dispatcher: native original action first, then every actually
-- registered PostHook for this exact class/method. Receiver and args are kept;
-- the sentinel is the native return value.
function HUDManager:activate_teammate_ability_radial(i, time_left, time_total)
    local target = self and self._teammate_panels and self._teammate_panels[i]
    local health = target and target._radial_health_panel
    if not health then return "native_ability_radial_unavailable" end
    local panel = health:child("radial_ability")
    local meter = panel:child("ability_meter")
    local icon = health:child("health_icon")
    time_total = time_total or time_left
    local progress_start = time_left / time_total
    panel:stop()
    panel:animate(HUDTeammate.activate_ability_radial_anim, time_left,
        progress_start, panel, meter, icon)
    -- Spies are installed only after the intentional native parent write.
    _G._parent_vis_writes = 0
    _G._parent_alpha_writes = 0
    _G._parent_color_writes = 0
    local function spy(obj, key, counter)
        local original = obj[key]
        obj[key] = function(self_obj, value)
            _G[counter] = _G[counter] + 1
            return original(self_obj, value)
        end
    end
    spy(panel, "set_visible", "_parent_vis_writes")
    spy(panel, "set_alpha", "_parent_alpha_writes")
    spy(panel, "set_color", "_parent_color_writes")
    dispatch(HUDManager, "activate_teammate_ability_radial", self, i,
        time_left, time_total)
    return "native_ability_radial_applied"
end

DB = {has = function() return true end}
Idstring = function(v) return v end
tweak_data.hud_icons = {get_icon_data = function(self, id, rect)
    return id, rect or {0, 0, 32, 32}
end}
_E._icon_cache = nil
_ability_icon:set_image("guis/dlcs/joy/textures/pd2/hud_pocket_ecm_jammer")

_E:refresh(_m)
'''


# Ordinary update with the native ability container hidden. The equipment root
# is the real local group; no player module is demanded.
HACKER_PREPARE = r'''
kyohud.settings.enable_player = false
kyohud.settings.enable_equipment = true
_E:refresh(_m)
_R:refresh_settings(_m)
_R:update(_m, 2.0, 0.1)

-- Place the native ability container inside the real equipment rectangle so a
-- visible parent genuinely overlaps the owned local group.
local function abs_xy(p)
    local ax, ay = 0, 0
    while p and p ~= panel_double do
        ax = ax + p:x()
        ay = ay + p:y()
        local parent = p:parent()
        if not parent then break end
        p = parent
    end
    return ax, ay
end
local ex, ey = abs_xy(_E._root)
local ew, eh = _E._root:w(), _E._root:h()
if ew <= 0 then ew = 120 end
if eh <= 0 then eh = 30 end
_ability_health_parent:set_shape(ex, ey, ew, eh)
_ability_parent:set_shape(0, 0, ew, eh)
_ability_parent:set_visible(false)
_ability_meter:set_shape(0, 0, ew, eh)
_ability_icon:set_shape(0, 0, ew, eh)
_ability_sentinel:set_shape(2, 2, 8, 8)

_pre_e_verify = (_E:verify() == true)
_pre_icon_ready = _E._rows[4]._icon ~= nil
    and _E._rows[4]._icon_descriptor ~= nil
    and _E._rows[4]._icon:visible() == true
    and _E._rows[4]._icon:texture_name()
        == "guis/dlcs/joy/textures/pd2/hud_pocket_ecm_jammer"
_pre_equipment_visible = (_E._root ~= nil and _E._root:visible() == true)
_pre_parent_hidden = (_ability_parent:visible() == false)
_pre_parent_alpha = _ability_parent:alpha()
_pre_meter_visible = (_ability_meter:visible() == true)
_pre_icon_visible = (_ability_icon:visible() == true)
_pre_meter_alpha = _ability_meter:alpha()
_pre_icon_alpha = _ability_icon:alpha()
_pre_meter_r = _ability_meter:color().r
_pre_grenade_visible = _gren:visible()
_pre_entry_count = #kyohud.hud.native_visibility._entries
_pre_activate_hooks = 0
for _, h in ipairs(Hooks._all) do
    if h.class == HUDManager and h.method == "activate_teammate_ability_radial"
        and h.kind == "post" then
        _pre_activate_hooks = _pre_activate_hooks + 1
    end
end
'''


ACTIVATE_AND_OBSERVE = r'''
inventory._jammer_data = {effect = "feedback", t = 1006}
_ability_parent:set_visible(false)
_emit_return = HUDManager.activate_teammate_ability_radial(
    _m, HUDManager.PLAYER_PANEL, 6, nil)

local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry, parent_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
    if e.object == _ability_parent then parent_entry = e end
end

local snap = _E:get_snapshot()
_post_e_verify = (_E:verify() == true)
_post_equipment_visible = (_E._root ~= nil and _E._root:visible() == true)
_post_parent_visible = (_ability_parent:visible() == true)
_post_parent_alpha = _ability_parent:alpha()
_post_parent_vis_writes = _parent_vis_writes or 0
_post_parent_alpha_writes = _parent_alpha_writes or 0
_post_parent_color_writes = _parent_color_writes or 0
_post_meter_visible = (_ability_meter:visible() == false)
_post_icon_visible = (_ability_icon:visible() == false)
_post_meter_alpha = _ability_meter:alpha()
_post_icon_alpha = _ability_icon:alpha()
_post_meter_r = _ability_meter:color().r
_post_meter_parent = (_ability_meter:parent() == _ability_parent)
_post_icon_parent = (_ability_icon:parent() == _ability_parent)
_post_health_parent_visible = (_ability_health_parent:visible() == true)
_post_sentinel_visible = (_ability_sentinel:visible() == true)
_post_sentinel_alpha = _ability_sentinel:alpha()
_post_sentinel_parent = (_ability_sentinel:parent() == _ability_health_parent)
_post_grenade_visible = _gren:visible()
_post_meter_entry_ok = meter_entry ~= nil and meter_entry.property == "visible"
    and meter_entry.old_value == true and meter_entry.applied_value == false
_post_icon_entry_ok = icon_entry ~= nil and icon_entry.property == "visible"
    and icon_entry.old_value == true and icon_entry.applied_value == false
_post_parent_leased = (parent_entry ~= nil)
_post_row6_visible = (_E._visible_rows and _E._visible_rows[6] == true) or false
_post_row6_label = _E._rows and _E._rows[6] and _E._rows[6]._label:text() or nil
_post_row6_value = _E._rows and _E._rows[6] and _E._rows[6]._value:text() or nil
_post_row6_progress = _E._rows and _E._rows[6] and _E._rows[6]._progress
_post_row6_verify = (_E._rows and _E._rows[6]
    and _E._rows[6]:verify() == true) or false
_post_row5_visible = (_E._visible_rows and _E._visible_rows[5] == true) or false
_post_row5_label = _E._rows and _E._rows[5] and _E._rows[5]._label:text() or nil
_post_row5_verify = (_E._rows and _E._rows[5]
    and _E._rows[5]:verify() == true) or false
_post_row4_visible = (_E._visible_rows and _E._visible_rows[4] == true) or false
_post_row4_verify = (_E._rows and _E._rows[4]
    and _E._rows[4]:verify() == true) or false
_post_charges = snap.projectile and snap.projectile.charges
    and snap.projectile.charges.raw
_post_cooldown = snap.cooldown and snap.cooldown.remaining
_post_jammer_effect = inventory._jammer_data and inventory._jammer_data.effect
'''


def hacker_lua():
    """Reusable local Hacker runtime: real equipment fixture + native ability
    panel + native-shaped activation dispatcher, then a clean ordinary update.
    """
    lua = _runtime()
    lua.execute(HACKER_FIXTURE)
    lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
    lua.execute(_read(EQUIPMENT_PATH))
    lua.execute(HACKER_PREPARE)
    return lua


class LocalHackerActiveTests(unittest.TestCase):
    def test_local_activation_leases_only_ability_bitmaps(self):
        lua = hacker_lua()
        g = lua.globals()

        self.assertTrue(bool(g._pre_e_verify),
            "precondition: equipment render must certify with ability hidden")
        self.assertTrue(bool(g._pre_equipment_visible),
            "precondition: equipment root must be visible before activation")
        self.assertTrue(bool(g._pre_parent_hidden),
            "precondition: native radial_ability must start hidden")
        self.assertTrue(bool(g._pre_meter_visible),
            "precondition: native ability_meter must start visible")
        self.assertTrue(bool(g._pre_icon_visible),
            "precondition: native ability_icon must start visible")
        self.assertAlmostEqual(float(g._pre_meter_alpha), .81, places=5)
        self.assertAlmostEqual(float(g._pre_icon_alpha), .67, places=5)
        self.assertEqual(float(g._pre_meter_r), 0.0,
            "precondition: native meter red channel starts stale at 0")
        self.assertTrue(bool(g._pre_grenade_visible),
            "precondition: existing native grenade source stays untouched")
        self.assertEqual(int(g._pre_activate_hooks), 1,
            "exactly one registered activation PostHook is dispatched")

        self.assertTrue(bool(g._pre_icon_ready),
            "equipped Hacker icon must render before activation")
        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_meter_visible),
            "RED: ACTIVE must hide radial_ability/ability_meter")
        self.assertTrue(bool(g._post_icon_visible),
            "RED: ACTIVE must hide radial_ability/ability_icon")
        self.assertTrue(bool(g._post_meter_entry_ok),
            "RED: ability_meter needs one visible=false native_visibility entry")
        self.assertTrue(bool(g._post_icon_entry_ok),
            "RED: ability_icon needs one visible=false native_visibility entry")
        self.assertFalse(bool(g._post_parent_leased),
            "native radial_ability container must never be leased")
        self.assertTrue(bool(g._post_parent_visible),
            "native radial_ability parent must stay visible")
        self.assertAlmostEqual(float(g._post_parent_alpha), .73, places=5)
        self.assertEqual(int(g._post_parent_vis_writes), 0,
            "feature must not write the native parent visibility")
        self.assertEqual(int(g._post_parent_alpha_writes), 0,
            "feature must not write the native parent alpha")
        self.assertEqual(int(g._post_parent_color_writes), 0,
            "feature must not write the native parent color")
        self.assertAlmostEqual(float(g._post_meter_alpha), .81, places=5,
            msg="native meter alpha must be preserved")
        self.assertAlmostEqual(float(g._post_icon_alpha), .67, places=5,
            msg="native icon alpha must be preserved")
        self.assertEqual(float(g._post_meter_r), 0.0,
            msg="native meter red channel must not be rewritten")
        self.assertTrue(bool(g._post_meter_parent))
        self.assertTrue(bool(g._post_icon_parent))
        self.assertTrue(bool(g._post_health_parent_visible),
            "native radial_health_panel must stay visible")
        self.assertTrue(bool(g._post_sentinel_visible),
            "third-party sibling sentinel must stay visible")
        self.assertAlmostEqual(float(g._post_sentinel_alpha), .55, places=5)
        self.assertTrue(bool(g._post_sentinel_parent))
        self.assertTrue(bool(g._post_grenade_visible),
            "existing grenade panel must remain visible")

        self.assertTrue(bool(g._post_e_verify),
            "RED: equipment render must certify after ACTIVE row 6 renders")
        self.assertTrue(bool(g._post_equipment_visible),
            "owned equipment group must stay visible")
        self.assertTrue(bool(g._post_row6_visible),
            "RED: ACTIVE row 6 must be visible without a runtime update")
        self.assertEqual(g._post_row6_label, "ACTIVE")
        self.assertEqual(g._post_row6_value, "6s")
        self.assertAlmostEqual(float(g._post_row6_progress), 1.0, places=5,
            msg="RED: ACTIVE row 6 progression must be remaining/duration = 1")
        self.assertTrue(bool(g._post_row6_verify),
            "RED: ACTIVE row 6 must pass the real row verifier")
        self.assertTrue(bool(g._post_row5_visible),
            "existing RECHARGE temporal row must stay visible")
        self.assertEqual(g._post_row5_label, "RECHARGE")
        self.assertTrue(bool(g._post_row5_verify),
            "existing RECHARGE row must stay certified")
        self.assertTrue(bool(g._post_row4_visible))
        self.assertTrue(bool(g._post_row4_verify),
            "equipped projectile cell must stay certified")
        self.assertEqual(float(g._post_charges), 1.0,
            "real projectile charges must stay 1 of 2")
        self.assertEqual(float(g._post_cooldown), 17.0,
            "existing recharge cooldown must stay 17s")
        self.assertEqual(g._post_jammer_effect, "feedback",
            "local inventory jammer corroboration must be actual")

    def test_extra_child_releases_two_leaves_and_equipment_guard(self):
        lua = hacker_lua()
        g = lua.globals()
        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_meter_visible),
            "precondition: ACTIVE hides ability_meter")
        self.assertTrue(bool(g._post_icon_visible),
            "precondition: ACTIVE hides ability_icon")
        self.assertTrue(bool(g._post_e_verify),
            "precondition: ACTIVE render certifies")

        lua.execute(r'''
local extra = _ability_parent:bitmap({name = "ky_test_extra_bitmap"})
extra:set_shape(0, 0, 4, 4)
extra:set_color(Color(1, .25, .25, 1))
extra:set_alpha(.25)
extra:set_visible(true)
_G._ability_extra = extra

_R:update(_m, 2.1, .1)

local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry, parent_entry, extra_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
    if e.object == _ability_parent then parent_entry = e end
    if e.object == extra then extra_entry = e end
end

_m1_meter_visible = (_ability_meter:visible() == true)
_m1_icon_visible = (_ability_icon:visible() == true)
_m1_meter_entry = (meter_entry ~= nil)
_m1_icon_entry = (icon_entry ~= nil)
_m1_parent_entry = (parent_entry ~= nil)
_m1_extra_entry = (extra_entry ~= nil)
_m1_e_root_hidden = (_E._root ~= nil and _E._root:visible() == false)
_m1_extra_visible = (extra:visible() == true)
_m1_extra_alpha = extra:alpha()
_m1_extra_parent = (extra:parent() == _ability_parent)
_m1_extra_x, _m1_extra_y = extra:x(), extra:y()
_m1_extra_w, _m1_extra_h = extra:w(), extra:h()
_m1_parent_visible = (_ability_parent:visible() == true)
_m1_parent_alpha = _ability_parent:alpha()
_m1_parent_vis_writes = _parent_vis_writes or 0
_m1_parent_alpha_writes = _parent_alpha_writes or 0
_m1_parent_color_writes = _parent_color_writes or 0
_m1_meter_parent = (_ability_meter:parent() == _ability_parent)
_m1_icon_parent = (_ability_icon:parent() == _ability_parent)
_m1_sentinel_visible = (_ability_sentinel:visible() == true)
_m1_sentinel_alpha = _ability_sentinel:alpha()
_m1_sentinel_parent = (_ability_sentinel:parent() == _ability_health_parent)
_m1_sentinel_x, _m1_sentinel_y = _ability_sentinel:x(), _ability_sentinel:y()
_m1_sentinel_w, _m1_sentinel_h = _ability_sentinel:w(), _ability_sentinel:h()
_m1_health_parent_visible = (_ability_health_parent:visible() == true)
''')

        self.assertTrue(bool(g._m1_meter_visible),
            "release must restore ability_meter visible")
        self.assertTrue(bool(g._m1_icon_visible),
            "release must restore ability_icon visible")
        self.assertFalse(bool(g._m1_meter_entry),
            "ability_meter must have no native_visibility entry after release")
        self.assertFalse(bool(g._m1_icon_entry),
            "ability_icon must have no native_visibility entry after release")
        self.assertFalse(bool(g._m1_parent_entry))
        self.assertFalse(bool(g._m1_extra_entry))
        self.assertTrue(bool(g._m1_e_root_hidden),
            "overlapping original guard must hide the owned equipment root")
        self.assertTrue(bool(g._m1_extra_visible))
        self.assertAlmostEqual(float(g._m1_extra_alpha), .25, places=5)
        self.assertTrue(bool(g._m1_extra_parent))
        self.assertEqual((float(g._m1_extra_x), float(g._m1_extra_y),
            float(g._m1_extra_w), float(g._m1_extra_h)), (0.0, 0.0, 4.0, 4.0),
            "extra bitmap must stay untouched")
        self.assertTrue(bool(g._m1_parent_visible))
        self.assertAlmostEqual(float(g._m1_parent_alpha), .73, places=5)
        self.assertEqual(int(g._m1_parent_vis_writes), 0,
            "release must not write the native parent visibility")
        self.assertEqual(int(g._m1_parent_alpha_writes), 0)
        self.assertEqual(int(g._m1_parent_color_writes), 0)
        self.assertTrue(bool(g._m1_meter_parent))
        self.assertTrue(bool(g._m1_icon_parent))
        self.assertTrue(bool(g._m1_sentinel_visible))
        self.assertAlmostEqual(float(g._m1_sentinel_alpha), .55, places=5)
        self.assertTrue(bool(g._m1_sentinel_parent))
        self.assertEqual((float(g._m1_sentinel_x), float(g._m1_sentinel_y),
            float(g._m1_sentinel_w), float(g._m1_sentinel_h)),
            (2.0, 2.0, 8.0, 8.0), "sentinel must stay untouched")
        self.assertTrue(bool(g._m1_health_parent_visible))

    def test_corrupt_row_text_releases_leaves_then_repairs(self):
        lua = hacker_lua()
        g = lua.globals()
        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_meter_visible),
            "precondition: ACTIVE hides ability_meter")
        self.assertTrue(bool(g._post_icon_visible),
            "precondition: ACTIVE hides ability_icon")
        self.assertTrue(bool(g._post_e_verify),
            "precondition: ACTIVE render certifies")

        lua.execute(r'''
local row6 = _E._rows[6]
local value = row6._value
local original_text = value:text()
local original_set_text = value.set_text
value:set_text("CORRUPT")
_R:update(_m, 2.001, .001)

_m2_row6_corrupt = (value:text() == "CORRUPT")
_m2_meter_visible = (_ability_meter:visible() == true)
_m2_icon_visible = (_ability_icon:visible() == true)
_m2_e_root_hidden = (_E._root ~= nil and _E._root:visible() == false)
_m2_e_verify = (_E:verify() == true)

original_set_text(value, original_text)
_R:update(_m, 2.1, .1)

_m2_original_text = original_text
_m2_repaired_value = value:text()
_m2_repaired_row6_verify = (row6:verify() == true)
_m2_repaired_meter_hidden = (_ability_meter:visible() == false)
_m2_repaired_icon_hidden = (_ability_icon:visible() == false)
''')

        self.assertTrue(bool(g._m2_row6_corrupt),
            "throttled update must leave the corrupt value untouched")
        self.assertTrue(bool(g._m2_meter_visible),
            "throttled release must restore ability_meter visible")
        self.assertTrue(bool(g._m2_icon_visible),
            "throttled release must restore ability_icon visible")
        self.assertTrue(bool(g._m2_e_root_hidden) or not bool(g._m2_e_verify),
            "owned equipment must hide or fail certification after corruption")
        self.assertEqual(g._m2_original_text, "6s",
            "original ACTIVE primitive must remain the 6s text")
        self.assertEqual(g._m2_repaired_value, g._m2_original_text,
            "original setter must repair the same primitive")
        self.assertTrue(bool(g._m2_repaired_row6_verify),
            "repaired ACTIVE row must pass its verifier")
        self.assertTrue(bool(g._m2_repaired_meter_hidden),
            "ordinary update must lease ability_meter again")
        self.assertTrue(bool(g._m2_repaired_icon_hidden),
            "ordinary update must lease ability_icon again")

    def test_idstring_activity_source_is_userdata(self):
        lua = hacker_lua()
        g = lua.globals()
        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_e_verify),
            "precondition: ACTIVE render must certify")
        self.assertTrue(bool(g._post_equipment_visible),
            "precondition: owned equipment root must stay visible")
        self.assertTrue(bool(g._post_meter_visible),
            "precondition: ACTIVE must lease ability_meter")
        self.assertTrue(bool(g._post_icon_visible),
            "precondition: ACTIVE must lease ability_icon")
        self.assertTrue(bool(g._post_meter_entry_ok),
            "precondition: ability_meter lease must be the visible=false entry")
        self.assertTrue(bool(g._post_icon_entry_ok),
            "precondition: ability_icon lease must be the visible=false entry")

        lua.execute(r'''
local native_path = "guis/dlcs/joy/textures/pd2/hud_pocket_ecm_jammer"
local ids, next_id = {}, 0
Idstring = function(v)
    if v == nil then v = "" end
    local key = ids[v]
    if key == nil then
        next_id = next_id + 1
        key = next_id
        ids[v] = key
    end
    local ud = newproxy(true)
    getmetatable(ud).__index = {key = function() return key end}
    return ud
end

local icon = _E._rows[4]._icon
icon.texture_name = function() return Idstring(native_path) end

local stable_a = Idstring(native_path)
local stable_b = Idstring(native_path)
local source = _E:get_hacker_activity_source()
_G._t1_stable_key = (stable_a:key() == stable_b:key())
_G._t1_source_type = type(icon:texture_name())
_G._t1_source_key = icon:texture_name():key()
_G._t1_expected_key = stable_a:key()
_G._t1_verify = (_E:_verify_hacker_activity(source) == true)
''')

        self.assertTrue(bool(g._t1_stable_key),
            "Idstring must map the same input to the same numeric key")
        self.assertEqual(g._t1_source_type, "userdata",
            "RED: native pocket texture must be exposed as actual userdata")
        self.assertIsNotNone(g._t1_source_key,
            "RED: activity source must expose a numeric key()")
        self.assertEqual(int(g._t1_source_key), int(g._t1_expected_key),
            "RED: activity source key must match the native pocket path")
        self.assertTrue(bool(g._t1_verify),
            "RED: _verify_hacker_activity must accept the userdata source")

    def test_throttled_update_advances_active_row_progress(self):
        lua = hacker_lua()
        g = lua.globals()
        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_e_verify),
            "precondition: ACTIVE render must certify")
        self.assertTrue(bool(g._post_meter_visible),
            "precondition: ACTIVE must lease ability_meter")
        self.assertTrue(bool(g._post_icon_visible),
            "precondition: ACTIVE must lease ability_icon")
        self.assertEqual(g._post_row6_value, "6s",
            "precondition: activation must render the initial 6s ACTIVE row")

        lua.execute(r'''
local row6 = _E._rows[6]
local value = row6._value
_game_clock:set_time(1000.01)
_R:update(_m, 2.01, .01)

local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
end

_G._t2_value_object_preserved = (row6._value == value)
_G._t2_value_text = value:text()
_G._t2_progress = row6._progress
_G._t2_meter_held = (meter_entry ~= nil and _ability_meter:visible() == false)
_G._t2_icon_held = (icon_entry ~= nil and _ability_icon:visible() == false)
_G._t2_row6_verify = (row6:verify() == true)
_G._t2_verify = (_E:_verify_hacker_activity(_E:get_hacker_activity_source()) == true)
''')

        self.assertTrue(bool(g._t2_value_object_preserved),
            "throttled update must reuse the same row6._value object")
        self.assertEqual(g._t2_value_text, "6s",
            "RED: throttled ACTIVE row must keep the 6s text")
        self.assertAlmostEqual(float(g._t2_progress), (6.0 - .01) / 6.0,
            delta=1e-6,
            msg="RED: throttled update must advance progress from the game clock")
        self.assertTrue(bool(g._t2_meter_held),
            "throttled update must hold ability_meter visible=false")
        self.assertTrue(bool(g._t2_icon_held),
            "throttled update must hold ability_icon visible=false")
        self.assertTrue(bool(g._t2_row6_verify),
            "throttled ACTIVE row must stay certified")
        self.assertTrue(bool(g._t2_verify),
            "real activity verifier must accept the source")

    def test_synchronous_other_native_effect_keeps_priority(self):
        lua = hacker_lua()
        g = lua.globals()

        self.assertTrue(bool(g._pre_e_verify),
            "precondition: equipment render must certify with ability hidden")

        lua.execute(r'''
local blocker = _ability_health_parent:bitmap({name = "radial_absorb_shield_active"})
blocker:set_shape(0, 0, _ability_parent:w(), _ability_parent:h())
blocker:set_color(Color(1, .3, .7, 1))
blocker:set_alpha(.42)
blocker:set_visible(false)
_G._ability_blocker = blocker
_G._blocker_expected_x, _G._blocker_expected_y = blocker:x(), blocker:y()
_G._blocker_expected_w, _G._blocker_expected_h = blocker:w(), blocker:h()
_G._blocker_hidden_e_verify = (_E:verify() == true)
blocker:set_visible(true)
_G._blocker_pre_visible = (blocker:visible() == true)
''')

        self.assertTrue(bool(g._blocker_hidden_e_verify),
            "precondition: equipment render must certify with blocker hidden")
        self.assertTrue(bool(g._blocker_pre_visible),
            "precondition: other native blocker must be visible before event E")

        lua.execute(ACTIVATE_AND_OBSERVE)

        lua.execute(r'''
local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry, blocker_entry, parent_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
    if e.object == _ability_blocker then blocker_entry = e end
    if e.object == _ability_parent then parent_entry = e end
end

_G._s_blocker_visible = (_ability_blocker:visible() == true)
_G._s_blocker_alpha = _ability_blocker:alpha()
_G._s_blocker_parent = (_ability_blocker:parent() == _ability_health_parent)
_G._s_blocker_x, _G._s_blocker_y = _ability_blocker:x(), _ability_blocker:y()
_G._s_blocker_w, _G._s_blocker_h = _ability_blocker:w(), _ability_blocker:h()
_G._s_blocker_entry = (blocker_entry ~= nil)
_G._s_meter_visible = (_ability_meter:visible() == true)
_G._s_icon_visible = (_ability_icon:visible() == true)
_G._s_meter_entry = (meter_entry ~= nil)
_G._s_icon_entry = (icon_entry ~= nil)
_G._s_parent_entry = (parent_entry ~= nil)
_G._s_parent_visible = (_ability_parent:visible() == true)
_G._s_parent_alpha = _ability_parent:alpha()
_G._s_parent_vis_writes = _parent_vis_writes or 0
_G._s_parent_alpha_writes = _parent_alpha_writes or 0
_G._s_parent_color_writes = _parent_color_writes or 0
_G._s_health_parent_visible = (_ability_health_parent:visible() == true)
''')

        self.assertFalse(bool(g._post_equipment_visible),
            "other indispensable native effect must keep priority and hide the owned root")
        self.assertTrue(bool(g._s_meter_visible),
            "ability_meter must be restored visible when the root yields")
        self.assertTrue(bool(g._s_icon_visible),
            "ability_icon must be restored visible when the root yields")
        self.assertFalse(bool(g._s_meter_entry),
            "ability_meter must have no native_visibility entry")
        self.assertFalse(bool(g._s_icon_entry),
            "ability_icon must have no native_visibility entry")

        self.assertTrue(bool(g._s_blocker_visible),
            "other native blocker must stay visible")
        self.assertTrue(bool(g._s_blocker_parent),
            "other native blocker must stay under the native health parent")
        self.assertFalse(bool(g._s_blocker_entry),
            "other native blocker must never be leased")
        self.assertAlmostEqual(float(g._s_blocker_alpha), .42, places=5)
        self.assertEqual((float(g._s_blocker_x), float(g._s_blocker_y),
            float(g._s_blocker_w), float(g._s_blocker_h)),
            (float(g._blocker_expected_x), float(g._blocker_expected_y),
            float(g._blocker_expected_w), float(g._blocker_expected_h)),
            "other native blocker shape must stay untouched")

        self.assertTrue(bool(g._s_parent_visible),
            "native radial_ability parent must stay visible")
        self.assertAlmostEqual(float(g._s_parent_alpha), .73, places=5)
        self.assertFalse(bool(g._s_parent_entry),
            "native radial_ability parent must never be leased")
        self.assertEqual(int(g._s_parent_vis_writes), 0,
            "feature must not write the native parent visibility")
        self.assertEqual(int(g._s_parent_alpha_writes), 0,
            "feature must not write the native parent alpha")
        self.assertEqual(int(g._s_parent_color_writes), 0,
            "feature must not write the native parent color")
        self.assertTrue(bool(g._s_health_parent_visible),
            "native radial_health_panel must stay visible")

    def test_remote_radial_cannot_release_certified_local_hacker(self):
        lua = hacker_lua()
        g = lua.globals()
        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_meter_visible),
            "precondition: ACTIVE must lease ability_meter")
        self.assertTrue(bool(g._post_icon_visible),
            "precondition: ACTIVE must lease ability_icon")
        self.assertTrue(bool(g._post_meter_entry_ok),
            "precondition: ability_meter lease must be the visible=false entry")
        self.assertTrue(bool(g._post_icon_entry_ok),
            "precondition: ability_icon lease must be the visible=false entry")
        self.assertTrue(bool(g._post_e_verify),
            "precondition: ACTIVE render must certify")

        lua.execute(r'''
local remote_panel = panel_double:panel({name = "teammate_remote_1"})
remote_panel:set_shape(0, 0, 432, 120)
remote_panel:set_visible(true)
local remote_player = remote_panel:panel({name = "player"})
remote_player:set_shape(0, 0, 432, 120)
remote_player:set_visible(true)
local remote_health = remote_player:panel({name = "radial_health_panel"})
remote_health:set_shape(0, 0, 432, 120)
remote_health:set_visible(true)
local remote_radial = remote_health:panel({name = "radial_ability"})
remote_radial:set_shape(0, 0, 432, 120)
remote_radial:set_visible(false)
local remote_meter = remote_radial:bitmap({name = "ability_meter"})
remote_meter:set_shape(0, 0, 32, 32)
remote_meter:set_visible(true)
local remote_icon = remote_radial:bitmap({name = "ability_icon"})
remote_icon:set_shape(0, 0, 32, 32)
remote_icon:set_visible(true)

managers.hud._teammate_panels[1] = {
    _ai = false,
    _peer_id = 2,
    _panel = remote_panel,
    _special_equipment = {},
}
_G._remote_parent_visible_before = (remote_radial:visible() == false)
_G._remote_meter_visible_before = (remote_meter:visible() == true)
_G._remote_icon_visible_before = (remote_icon:visible() == true)

_R:update(_m, 2.01, .01)

local nv = kyohud.hud.native_visibility
local local_meter_entry, local_icon_entry
local remote_parent_entry, remote_meter_entry, remote_icon_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then local_meter_entry = e end
    if e.object == _ability_icon then local_icon_entry = e end
    if e.object == remote_radial then remote_parent_entry = e end
    if e.object == remote_meter then remote_meter_entry = e end
    if e.object == remote_icon then remote_icon_entry = e end
end

_G._reg_local_meter_held = (_ability_meter:visible() == false)
_G._reg_local_icon_held = (_ability_icon:visible() == false)
_G._reg_local_meter_entry_ok = local_meter_entry ~= nil
    and local_meter_entry.property == "visible"
    and local_meter_entry.applied_value == false
_G._reg_local_icon_entry_ok = local_icon_entry ~= nil
    and local_icon_entry.property == "visible"
    and local_icon_entry.applied_value == false
_G._reg_e_verify = (_E:verify() == true)
_G._reg_e_root_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._reg_remote_parent_hidden = (remote_radial:visible() == false)
_G._reg_remote_meter_visible = (remote_meter:visible() == true)
_G._reg_remote_icon_visible = (remote_icon:visible() == true)
_G._reg_remote_parent_entry = (remote_parent_entry ~= nil)
_G._reg_remote_meter_entry = (remote_meter_entry ~= nil)
_G._reg_remote_icon_entry = (remote_icon_entry ~= nil)
''')

        self.assertTrue(bool(g._remote_parent_visible_before),
            "precondition: remote radial_ability parent must start hidden")
        self.assertTrue(bool(g._remote_meter_visible_before),
            "precondition: remote ability_meter must start visible")
        self.assertTrue(bool(g._remote_icon_visible_before),
            "precondition: remote ability_icon must start visible")

        self.assertTrue(bool(g._reg_local_meter_held),
            "RED: remote radial_ability must not release ability_meter")
        self.assertTrue(bool(g._reg_local_icon_held),
            "RED: remote radial_ability must not release ability_icon")
        self.assertTrue(bool(g._reg_local_meter_entry_ok),
            "RED: ability_meter must keep its visible=false native_visibility entry")
        self.assertTrue(bool(g._reg_local_icon_entry_ok),
            "RED: ability_icon must keep its visible=false native_visibility entry")
        self.assertTrue(bool(g._reg_e_verify),
            "RED: certified equipment render must survive the remote entry")
        self.assertTrue(bool(g._reg_e_root_visible),
            "RED: owned equipment root must stay visible")
        self.assertFalse(bool(g._reg_remote_parent_entry),
            "hidden remote radial_ability parent must never be leased")
        self.assertTrue(bool(g._reg_remote_parent_hidden),
            "hidden remote radial_ability parent must stay hidden")
        self.assertTrue(bool(g._reg_remote_meter_visible),
            "hidden remote ability_meter must stay untouched")
        self.assertTrue(bool(g._reg_remote_icon_visible),
            "hidden remote ability_icon must stay untouched")
        self.assertFalse(bool(g._reg_remote_meter_entry),
            "hidden remote ability_meter must never be leased")
        self.assertFalse(bool(g._reg_remote_icon_entry),
            "hidden remote ability_icon must never be leased")


if __name__ == "__main__":
    unittest.main()
