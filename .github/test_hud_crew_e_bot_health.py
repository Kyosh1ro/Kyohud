"""Crew Card bot health -- tranche bots: health only, no armor layer for bots.

One compact transition test against lua/hud/components/crew_card.lua via
lupa.luajit21.  Reuses _lua() from test_hud_crew_card.

Bot contract (tranche bots health-only):
  - Bot (ai=true) with valid health ratio .42 provenance bot_host:
    _health_text "42%", _armor_fill / _ar_bg / _armor_text all invisible
    (no fake zero armor for bots).
  - Transition: same card human health .8 armor .5 => armor text hidden (no % visible).
  - Transition back: bot health unknown valid false => "--", armor invisible.
  - Primitive identity preserved across all transitions.
  - Certification: after bot render, manually set each armor primitive visible
    => verify false; update => verify true, same object.  Loop is Lua-side,
    not test-side.
  - Bleedout: condition_text stays independent, not snapshot-converted.

RED: production crew_card.lua currently always shows armor row visible.
"""
import unittest

from test_hud_crew_card import _lua


class CrewCardBotHealthTransitionTests(unittest.TestCase):

    def test_bot_health_only_no_armor_layer_transition_and_certification(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key)
                if key == "menu_russian" then return "Dallas"
                elseif key == "menu_american" then return "Hoxton"
                elseif key == "menu_german" then return "Wolf"
                elseif key == "menu_spanish" then return "Chains"
                elseif key == "ky_hud_crew_ai" then return "IA"
                else return "Loc:" .. tostring(key) end
            end

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "bot_hp")
            inst:set_geometry(0, 0, 280, 120)

            ----------------------------------------------------------------
            -- Phase 1: bot ai=true, health valid ratio .42, bot_host
            ----------------------------------------------------------------
            local bot_valid = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "russian",
                health = {current = 42, total = 100, ratio = 0.42,
                          valid = true, provenance = "bot_host"},
                armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }

            _up1 = inst:update(bot_valid, 0)
            _v1 = inst:verify()
            _hp1 = inst._health_text:text()
            _ar_bg_v1 = inst._ar_bg:visible()
            _ar_fl_v1 = inst._armor_fill:visible()
            _ar_tx_v1 = inst._armor_text:visible()
            _wp1 = inst._weapon_text:text()
            _eq1 = inst._equipment_text:text()

            local ref_nt = inst._name_text
            local ref_ht = inst._health_text
            local ref_af = inst._armor_fill
            local ref_at = inst._armor_text
            local ref_ab = inst._ar_bg
            local ref_wt = inst._weapon_text
            local ref_et = inst._equipment_text

            ----------------------------------------------------------------
            -- Phase 2: transition same card -> human health .8 armor .5
            ----------------------------------------------------------------
            local human = {
                name = "Tester", level = 10, rank = 2, ai = false,
                peer_id = 1, character_name = "spanish",
                health = {current = 80, total = 100, ratio = 0.8,
                          valid = true, provenance = "network_quantized"},
                armor = {current = 2.5, total = 5, ratio = 0.5,
                         valid = true, provenance = "network_quantized"},
                weapon = {name_id = "wpn_test",
                    ammo = {current_clip = 10, reserve = 40,
                            provenance = "network_synced"}},
                equipment = nil, interaction = nil,
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }

            _up2 = inst:update(human, 1)
            _v2 = inst:verify()
            _hp2 = inst._health_text:text()
            _ar_tx2 = inst._armor_text:text()
            _ar_bg_v2 = inst._ar_bg:visible()
            _ar_fl_v2 = inst._armor_fill:visible()
            _ar_tx_v2 = inst._armor_text:visible()

            ----------------------------------------------------------------
            -- Phase 3: transition back -> bot health unknown valid=false
            ----------------------------------------------------------------
            local bot_unk = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "american",
                health = {valid = false},
                armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }

            _up3 = inst:update(bot_unk, 2)
            _v3 = inst:verify()
            _hp3 = inst._health_text:text()
            _ar_bg_v3 = inst._ar_bg:visible()
            _ar_fl_v3 = inst._armor_fill:visible()
            _ar_tx_v3 = inst._armor_text:visible()

            ----------------------------------------------------------------
            -- Primitive identity across all 3 transitions
            ----------------------------------------------------------------
            _same_nt = (inst._name_text == ref_nt)
            _same_ht = (inst._health_text == ref_ht)
            _same_af = (inst._armor_fill == ref_af)
            _same_at = (inst._armor_text == ref_at)
            _same_ab = (inst._ar_bg == ref_ab)
            _same_wt = (inst._weapon_text == ref_wt)
            _same_et = (inst._equipment_text == ref_et)

            ----------------------------------------------------------------
            -- Certification: Lua-side loop over 3 armor primitives
            -- After bot render (armor must be invisible), set visible =>
            -- verify false, update => verify true, same object.
            ----------------------------------------------------------------
            local cn = {"at", "ab", "af"}
            local cp = {"_armor_text", "_ar_bg", "_armor_fill"}
            for i, pn in ipairs(cp) do
                local prim = inst[pn]
                prim:set_visible(true)
                _G["cert_" .. cn[i] .. "_bad"] = inst:verify()
                inst:update(bot_unk, 2 + i)
                _G["cert_" .. cn[i] .. "_ok"] = inst:verify()
                _G["cert_" .. cn[i] .. "_same"] = (inst[pn] == prim)
            end

            ----------------------------------------------------------------
            -- Bleedout: condition_text independent, not snapshot-converted
            ----------------------------------------------------------------
            local bot_bleed = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "german",
                health = nil, armor = nil, weapon = nil,
                equipment = nil, interaction = nil,
                downs = 1, condition_text = "bleed_out",
                condition_icon = nil, condition_phase = "bleedout"
            }

            _up4 = inst:update(bot_bleed, 4)
            _v4 = inst:verify()
            _st4 = inst._status_text:text()
            _hp4 = inst._health_text:text()
            _ar_tx_v4 = inst._armor_text:visible()

            inst:destroy()
        ''')
        g = lua.globals()

        # Phase 1: bot valid health, armor hidden
        self.assertTrue(bool(g._up1), "update must succeed for bot with valid health")
        self.assertTrue(bool(g._v1), "verify must be true after bot update")
        self.assertEqual(g._hp1, "42%",
            "bot health valid ratio .42 -> '42%'")
        self.assertFalse(bool(g._ar_bg_v1),
            "bot: _ar_bg must be invisible (no armor layer)")
        self.assertFalse(bool(g._ar_fl_v1),
            "bot: _armor_fill must be invisible (no armor layer)")
        self.assertFalse(bool(g._ar_tx_v1),
            "bot: _armor_text must be invisible (no armor number)")
        self.assertEqual(g._wp1, "---",
            "bot weapon unchanged -> '---'")
        self.assertEqual(g._eq1, "--",
            "bot equipment unchanged -> '--'")

        # Phase 2: human transition, armor visible
        self.assertTrue(bool(g._up2), "update must succeed for human")
        self.assertTrue(bool(g._v2), "verify must be true for human")
        self.assertEqual(g._hp2, "80%")
        self.assertEqual(g._ar_tx2, "50%",
            "human armor ratio .5 -> '50%'")
        self.assertTrue(bool(g._ar_bg_v2),
            "human: _ar_bg must be visible")
        self.assertTrue(bool(g._ar_fl_v2),
            "human: _armor_fill must be visible")
        self.assertFalse(bool(g._ar_tx_v2),
            "human: _armor_text must be hidden (no % armor visible)")

        # Phase 3: back to bot unknown, armor hidden again
        self.assertTrue(bool(g._up3), "update must succeed for bot unknown")
        self.assertTrue(bool(g._v3), "verify must be true for bot unknown")
        self.assertEqual(g._hp3, "--",
            "bot health unknown -> '--'")
        self.assertFalse(bool(g._ar_bg_v3),
            "bot: _ar_bg invisible again")
        self.assertFalse(bool(g._ar_fl_v3),
            "bot: _armor_fill invisible again")
        self.assertFalse(bool(g._ar_tx_v3),
            "bot: _armor_text invisible again")

        # Primitive identity preserved
        for attr in ("_same_nt", "_same_ht", "_same_af", "_same_at",
                      "_same_ab", "_same_wt", "_same_et"):
            self.assertTrue(bool(g[attr]),
                f"primitive identity preserved: {attr}")

        # Certification: Lua-side loop results
        for prefix in ("cert_at", "cert_ab", "cert_af"):
            self.assertFalse(bool(g[f"{prefix}_bad"]),
                f"verify false after {prefix} visibility corruption")
            self.assertTrue(bool(g[f"{prefix}_ok"]),
                f"verify true after update repairs {prefix}")
            self.assertTrue(bool(g[f"{prefix}_same"]),
                f"update reuses same {prefix} reference")

        # Bleedout: condition independent, not snapshot
        self.assertTrue(bool(g._up4), "update must succeed for bleedout bot")
        self.assertTrue(bool(g._v4), "verify true for bleedout bot")
        self.assertEqual(g._st4, "",
            "minimal bot presentation has no condition row")
        self.assertEqual(g._hp4, "--",
            "bleedout bot nil health -> '--'")
        self.assertFalse(bool(g._ar_tx_v4),
            "bleedout bot: armor text stays invisible")


if __name__ == "__main__":
    unittest.main()
