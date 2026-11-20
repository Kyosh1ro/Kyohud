"""Remote crew per-deck H5 sync -- RED-first port of every local deck subsystem.

The local player's per-deck replacements (Hacker ACTIVE, Kingpin absorb, dodge,
Maniac stacks, Stoic reserve, COPR, delayed damage and damage feedback) already
read exact native leaves, render owned primitives and lease the native leaf
alpha through the H5 group. The remote crew cards must expose the same contract
for every teammate slot, never assuming the local PLAYER_PANEL slot.

Fixture model:
- ``test_hud_crew_online_ammo._crew_lua`` builds the full crew stack.
- ``test_hud_crew_online_ammo.RENDER_SETUP`` installs the native-shaped
  PlayerManager publication fixture and wrapping hooks.
- ``lua/hud/actors.lua`` is reloaded in both real contexts so genuine
  callbacks are registered, exactly as the online ammo/native tests do.

Each deck test installs the ally native leaf under teammate_panels[2] (a REMOTE
slot, never the local PLAYER_PANEL), runs the ordinary crew update, and then
runs the runtime update that executes the native-priority guard. It asserts:
(a) the owned crew-card replacement exists, is visible and certifies;
(b) the native leaf is leased to alpha 0 by the crew group;
(c) the guard no longer yields the crew block for that leaf.

RED state: before the production port, crew_card.lua owns no deck primitive and
runtime.lua has no ``_sync_crew_perkdeck``; every owned-replacement assertion
fails explicitly instead of silently skipping.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_crew_online_ammo import _crew_lua, RENDER_SETUP, ACTORS_PATH


def _runtime():
    lua, ok = _crew_lua()
    assert ok, "RED: lua/hud/crew.lua must exist"
    lua.execute(RENDER_SETUP)
    # The base fixture records hooks; RENDER_SETUP wraps only later installs.
    lua.execute('kyohud.hud._installed_hooks.KyohHUD_Actors_Revives=nil')
    for context in ('lib/managers/playermanager', 'lib/managers/hudmanagerpd2'):
        lua.globals().RequiredScript = context
        lua.execute(ACTORS_PATH.read_text(encoding='utf-8-sig'))
    lua.execute(r'''
        kyohud.settings.enable_hud_foundation = true
        kyohud.settings.enable_crew = true
        kyohud.settings.hud_scale = 1.0
        panel_double:set_shape(0, 0, 1920, 1080)

        A = kyohud.hud.actors
        R = kyohud.hud.runtime
        C = kyohud.hud.crew
        A:refresh_crew(managers.hud, 0)
        managers.player:set_synced_ammo_info(2, 1, 30, 7, 67, 120)
        managers.player:set_synced_ammo_info(2, 2, 40, 12, 95, 160)
        R:mount(managers.hud)
        C:mount(managers.hud)
        C:update(managers.hud, 1.0, 0.05)

        local cr = C._root
        local ep = panel_double:panel({name = "deck_native_slot2"})
        ep:set_shape(cr:x(), cr:y(), cr:w(), cr:h())
        ep:set_visible(true)
        local np = ep:panel({name = "player"})
        np:set_shape(0, 0, cr:w(), cr:h())
        np:set_visible(true)
        local radial = np:panel({name = "radial_health_panel"})
        radial:set_shape(0, 0, cr:w(), cr:h())
        radial:set_visible(true)
        managers.hud._teammate_panels[2]._panel = ep
        _G.deck_entry = ep
        _G.deck_player = np
        _G.deck_radial = radial
    ''')
    return lua


def _run(lua, prim_field, leaf_names):
    names = ", ".join('"%s"' % name for name in leaf_names)
    lua.execute(r'''
        C:update(managers.hud, 1.2, 0.05)
        R:update(managers.hud, 1.3, 0.05)
        R:update(managers.hud, 1.4, 0.05)
        local card = C._cards[2]
        _owned_exists = card ~= nil and card[%r] ~= nil
        _owned_visible = _owned_exists and card[%r]:visible() == true
        _crew_visible = C._root and C._root:visible() or false
        _crew_verify = C:_verify_render()
        _leaf_alphas = {}
        for _, name in ipairs({%s}) do
            local leaf = deck_radial:child(name)
            if not leaf then
                local delayed = deck_radial:child("radial_delayed_damage")
                leaf = delayed and delayed:child(name) or nil
            end
            _leaf_alphas[name] = leaf and leaf:alpha() or -1
        end
    ''' % (prim_field, prim_field, names))


class CrewPerkdeckBase(unittest.TestCase):
    def _assert_owned(self, lua, prim_field, leaf_names):
        g = lua.globals()
        self.assertIs(bool(g._owned_exists), True,
            f"RED: Card.{prim_field} must be an owned crew-card primitive")
        self.assertIs(bool(g._owned_visible), True,
            f"RED: Card.{prim_field} must be visible for the ally deck state")
        self.assertIs(bool(g._crew_verify), True,
            "RED: crew render including the owned deck primitive must certify")
        self.assertIs(bool(g._crew_visible), True,
            "RED: the native-priority guard must not yield the crew block for a handled leaf")
        for name in leaf_names:
            alpha = g._leaf_alphas[name]
            self.assertIsNotNone(alpha,
                f"RED: native leaf {name} must exist under the ally radial panel")
            self.assertGreaterEqual(float(alpha), 0.0,
                f"RED: native leaf {name} must be readable (not a missing sentinel)")
            self.assertAlmostEqual(float(alpha), 0.0, places=4,
                msg=f"RED: the crew H5 group must lease native {name} to alpha 0")


class HackerActiveDeckTests(CrewPerkdeckBase):
    def test_hacker_active_renders_on_armor_and_releases_native_ability(self):
        lua = _runtime()
        lua.execute(r'''
            local ability = deck_radial:panel({name = "radial_ability"})
            ability:set_shape(0, 0, 60, 60)
            ability:set_visible(true)
            ability:set_alpha(1)
            local meter = ability:bitmap({name = "ability_meter"})
            meter:set_shape(0, 0, 60, 60)
            meter:set_visible(true)
            meter:set_color(Color(1, 0.5, 1, 1))
            local icon = ability:bitmap({name = "ability_icon", visible = true})
            icon:set_shape(20, 20, 20, 20)
        ''')
        _run(lua, "_deck_hacker_fill", ["radial_ability"])
        self._assert_owned(lua, "_deck_hacker_fill", ["radial_ability"])


class KingpinDeckTests(CrewPerkdeckBase):
    def test_kingpin_absorb_renders_and_releases_native_absorb_leaves(self):
        lua = _runtime()
        lua.execute(r'''
            local shield = deck_radial:bitmap({name = "radial_absorb_shield_active"})
            shield:set_shape(0, 0, 60, 60)
            shield:set_visible(true)
            shield:set_alpha(1)
            shield:set_color(Color(1, 1, 1, 1))
            local health = deck_radial:bitmap({name = "radial_absorb_health_active"})
            health:set_shape(0, 0, 60, 60)
            health:set_visible(true)
            health:set_alpha(1)
            health:set_color(Color(1, 1, 1, 1))
        ''')
        _run(lua, "_deck_kingpin_shield",
            ["radial_absorb_shield_active", "radial_absorb_health_active"])
        self._assert_owned(lua, "_deck_kingpin_shield",
            ["radial_absorb_shield_active", "radial_absorb_health_active"])


class DodgeDeckTests(CrewPerkdeckBase):
    def test_dodge_renders_and_releases_native_radial_custom(self):
        lua = _runtime()
        lua.execute(r'''
            local custom = deck_radial:bitmap({name = "radial_custom"})
            custom:set_shape(0, 0, 60, 60)
            custom:set_visible(true)
            custom:set_alpha(0.8)
            custom:set_color(Color(1, 0.65, 1, 1))
        ''')
        _run(lua, "_deck_dodge", ["radial_custom"])
        self._assert_owned(lua, "_deck_dodge", ["radial_custom"])


class ManiacDeckTests(CrewPerkdeckBase):
    def test_maniac_stacks_render_and_release_native_info_meter(self):
        lua = _runtime()
        lua.execute(r'''
            local fg = deck_radial:bitmap({name = "radial_info_meter"})
            fg:set_shape(0, 0, 60, 60)
            fg:set_visible(true)
            fg:set_alpha(0.7)
            fg:set_color(Color(1, 0.7, 1, 1))
            local bg = deck_radial:bitmap({name = "radial_info_meter_bg"})
            bg:set_shape(0, 0, 60, 60)
            bg:set_visible(true)
            bg:set_alpha(0.5)
            bg:set_color(Color(1, 1, 1, 1))
        ''')
        _run(lua, "_deck_maniac",
            ["radial_info_meter", "radial_info_meter_bg"])
        self._assert_owned(lua, "_deck_maniac",
            ["radial_info_meter", "radial_info_meter_bg"])


class StoicReserveDeckTests(CrewPerkdeckBase):
    def test_stoic_reserve_renders_and_releases_native_rip(self):
        lua = _runtime()
        lua.execute(r'''
            local rip = deck_radial:bitmap({name = "radial_rip"})
            rip:set_shape(0, 0, 60, 60)
            rip:set_visible(true)
            rip:set_alpha(0.9)
            rip:set_color(Color(1, 0.4, 1, 1))
            local rip_bg = deck_radial:bitmap({name = "radial_rip_bg"})
            rip_bg:set_shape(0, 0, 60, 60)
            rip_bg:set_visible(true)
            rip_bg:set_alpha(0.6)
            rip_bg:set_color(Color(1, 1, 1, 1))
        ''')
        _run(lua, "_deck_stoic_fill", ["radial_rip", "radial_rip_bg"])
        self._assert_owned(lua, "_deck_stoic_fill", ["radial_rip", "radial_rip_bg"])


class CoprDeckTests(CrewPerkdeckBase):
    def test_copr_ratio_renders_and_releases_native_overlay_notches(self):
        lua = _runtime()
        lua.execute(r'''
            local copr = deck_radial:panel({name = "copr_overlay_panel"})
            copr:set_shape(0, 0, 60, 60)
            copr:set_visible(true)
            local notch = copr:bitmap({name = "0"})
            notch:set_shape(0, 0, 60, 60)
            notch:set_visible(true)
            notch:set_alpha(0.8)
            notch:set_color(Color(1, 0.7, 1, 1))
        ''')
        _run(lua, "_deck_copr_fill", [])
        self._assert_owned(lua, "_deck_copr_fill", [])
        lua.execute(r'''
            local copr = deck_radial:child("copr_overlay_panel")
            local notch = copr and copr:child("0") or nil
            _copr_notch_exists = notch ~= nil
            _copr_notch_alpha = notch and notch:alpha() or -1
        ''')
        g = lua.globals()
        self.assertIs(bool(g._copr_notch_exists), True,
            "RED: native COPR notch 0 must exist")
        self.assertAlmostEqual(float(g._copr_notch_alpha), 0.0, places=4,
            msg="RED: the crew H5 group must lease the native COPR notch to alpha 0")


class DelayedDamageDeckTests(CrewPerkdeckBase):
    def test_delayed_damage_renders_and_releases_native_delayed_leaves(self):
        lua = _runtime()
        lua.execute(r'''
            local delayed = deck_radial:panel({name = "radial_delayed_damage"})
            delayed:set_shape(0, 0, 60, 60)
            delayed:set_visible(true)
            local armor = delayed:bitmap({name = "radial_delayed_damage_armor"})
            armor:set_shape(0, 0, 60, 60)
            armor:set_visible(true)
            armor:set_alpha(0.8)
            local health = delayed:bitmap({name = "radial_delayed_damage_health"})
            health:set_shape(0, 0, 60, 60)
            health:set_visible(true)
            health:set_alpha(0.6)
        ''')
        _run(lua, "_deck_delayed_armor",
            ["radial_delayed_damage_armor", "radial_delayed_damage_health"])
        self._assert_owned(lua, "_deck_delayed_armor",
            ["radial_delayed_damage_armor", "radial_delayed_damage_health"])


class DamageFeedbackDeckTests(CrewPerkdeckBase):
    def test_damage_feedback_renders_edges_and_releases_native_indicator(self):
        lua = _runtime()
        lua.execute(r'''
            local indicator = deck_radial:bitmap({name = "damage_indicator"})
            indicator:set_shape(0, 0, 60, 60)
            indicator:set_visible(true)
            indicator:set_alpha(0.75)
            indicator:set_color(Color(1, 1, 1, 1))
        ''')
        _run(lua, "_deck_damage_top", ["damage_indicator"])
        self._assert_owned(lua, "_deck_damage_top", ["damage_indicator"])


if __name__ == "__main__":
    unittest.main()
