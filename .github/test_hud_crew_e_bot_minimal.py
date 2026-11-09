"""Bot minimal presentation -- crew_card.lua: name only + blue health bar (RED tracer).

Bot contract (minimal):
  - Bot (ai=true) name: localized "Dallas" WITHOUT "IA" suffix, even when name is nil.
  - No visible square: _peer_dot hidden (visible=false).
  - _rank_text and ALL other texts except _name_text hidden.
  - _health_fill and _hp_bg visible (blue health bar, fixed blue RGB(.35,.70,.95)).
  - Health ratio .42 then .1: color uses fixed blue {r=.35,g=.70,b=.95}, NOT threshold.
  - Unknown health (valid=false): fill width 0, no invented number, root visible.
  - Human presentation: name+peer color, gauges visible, %HP/armor text hidden.
  - After bot->human->bot transition: no visible leak, same primitives.
  - Certification: making weapon text visible or wrong fill color => verify false,
    then update restores true with same objects.

RED: production crew_card.lua currently shows "Dallas IA" and health_text visible.
First expected failure: name "Dallas IA" != "Dallas" or health_text visible.
"""
import unittest

from test_hud_crew_card import _lua


class CrewCardBotMinimalTransitionTests(unittest.TestCase):

    def test_bot_health_bar_ratio_and_color(self):
        """Bot health bar: ratio .42 then .1 with color (.1,.7,.9), valid=false => width 0."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key)
                if key == "menu_russian" then return "Dallas"
                else return "Loc:" .. tostring(key) end
            end

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card

            local scales = {0.95, 1.0, 1.05}
            _results = {}
            local idx = 0

            for _, e in ipairs(scales) do
                local inst = CC.new(parent, "bot_ratio_" .. tostring(e))
                inst:set_geometry(0, 0, 280 * e, 120 * e)

                local bot_ratio_42 = {
                    name = nil, level = nil, rank = nil, ai = true,
                    peer_id = nil, character_name = "russian",
                    color = {r = 0.35, g = 0.70, b = 0.95},
                    health = {current = 42, total = 100, ratio = 0.42,
                              valid = true, provenance = "bot_host"},
                    armor = nil, weapon = nil, equipment = nil, interaction = nil,
                    downs = 0, condition_text = "normal",
                    condition_icon = nil, condition_phase = nil
                }

                local up1 = inst:update(bot_ratio_42, 0)
                local v1 = inst:verify()
                local hp_bg_w1 = inst._hp_bg:w()
                local hp_fill_w1 = inst._health_fill:w()
                local hp_fill_c1 = inst._health_fill:color()
                local ratio1 = hp_fill_w1 / hp_bg_w1

                idx = idx + 1
                _results[idx] = {
                    scale = e, up = up1, verify = v1,
                    hp_bg_w = hp_bg_w1, hp_fill_w = hp_fill_w1,
                    ratio = ratio1,
                    r = hp_fill_c1.r, g = hp_fill_c1.g, b = hp_fill_c1.b
                }

                local bot_ratio_10 = {
                    name = nil, level = nil, rank = nil, ai = true,
                    peer_id = nil, character_name = "russian",
                    color = {r = 0.35, g = 0.70, b = 0.95},
                    health = {current = 10, total = 100, ratio = 0.1,
                              valid = true, provenance = "bot_host"},
                    armor = nil, weapon = nil, equipment = nil, interaction = nil,
                    downs = 0, condition_text = "normal",
                    condition_icon = nil, condition_phase = nil
                }

                local up2 = inst:update(bot_ratio_10, 1)
                local v2 = inst:verify()
                local hp_fill_w2 = inst._health_fill:w()
                local hp_fill_c2 = inst._health_fill:color()
                local ratio2 = hp_fill_w2 / hp_bg_w1

                idx = idx + 1
                _results[idx] = {
                    scale = e, up = up2, verify = v2,
                    hp_bg_w = hp_bg_w1, hp_fill_w = hp_fill_w2,
                    ratio = ratio2,
                    r = hp_fill_c2.r, g = hp_fill_c2.g, b = hp_fill_c2.b
                }

                local bot_invalid = {
                    name = nil, level = nil, rank = nil, ai = true,
                    peer_id = nil, character_name = "russian",
                    color = {r = 0.35, g = 0.70, b = 0.95},
                    health = {valid = false},
                    armor = nil, weapon = nil, equipment = nil, interaction = nil,
                    downs = 0, condition_text = "normal",
                    condition_icon = nil, condition_phase = nil
                }

                local up3 = inst:update(bot_invalid, 2)
                local v3 = inst:verify()
                local hp_fill_w3 = inst._health_fill:w()
                local root_v3 = inst.root:visible()
                local hp_text_v3 = inst._health_text:visible()

                idx = idx + 1
                _results[idx] = {
                    scale = e, up = up3, verify = v3,
                    hp_fill_w = hp_fill_w3, root_visible = root_v3,
                    hp_text_visible = hp_text_v3
                }

                inst:destroy()
            end
        ''')
        g = lua.globals()
        results = g._results

        for i in range(3):
            e = [0.95, 1.0, 1.05][i]
            base = i * 3

            r1 = results[base + 1]
            self.assertTrue(bool(r1['up']), f"scale {e}: update ratio .42 must succeed")
            self.assertTrue(bool(r1['verify']), f"scale {e}: verify ratio .42 must be true")
            self.assertAlmostEqual(float(r1['ratio']), 0.42, places=2,
                msg=f"scale {e}: fill width / hp_bg width must be close to .42")
            self.assertAlmostEqual(float(r1['r']), 0.35, delta=0.02,
                msg=f"scale {e}: color .r must be .35 (fixed blue)")
            self.assertAlmostEqual(float(r1['g']), 0.70, delta=0.02,
                msg=f"scale {e}: color .g must be .70 (fixed blue)")
            self.assertAlmostEqual(float(r1['b']), 0.95, delta=0.02,
                msg=f"scale {e}: color .b must be .95 (fixed blue)")

            r2 = results[base + 2]
            self.assertTrue(bool(r2['up']), f"scale {e}: update ratio .1 must succeed")
            self.assertTrue(bool(r2['verify']), f"scale {e}: verify ratio .1 must be true")
            self.assertAlmostEqual(float(r2['ratio']), 0.1, places=2,
                msg=f"scale {e}: fill width / hp_bg width must be close to .1")
            self.assertAlmostEqual(float(r2['r']), 0.35, delta=0.02,
                msg=f"scale {e}: color .r must stay .35 (fixed blue)")
            self.assertAlmostEqual(float(r2['g']), 0.70, delta=0.02,
                msg=f"scale {e}: color .g must stay .70 (fixed blue)")
            self.assertAlmostEqual(float(r2['b']), 0.95, delta=0.02,
                msg=f"scale {e}: color .b must stay .95 (fixed blue)")

            r3 = results[base + 3]
            self.assertTrue(bool(r3['up']), f"scale {e}: update valid=false must succeed")
            self.assertTrue(bool(r3['verify']), f"scale {e}: verify valid=false must be true")
            self.assertAlmostEqual(float(r3['hp_fill_w']), 0.0, places=1,
                msg=f"scale {e}: fill width must be 0 when valid=false")
            self.assertTrue(bool(r3['root_visible']),
                f"scale {e}: root panel must remain visible")
            self.assertFalse(bool(r3['hp_text_visible']),
                f"scale {e}: health_text must be invisible when valid=false")

    def test_bot_minimal_name_only_blue_health_bar_transition(self):
        """Bot->human->bot: minimal bot presentation, human full, bot again clean."""
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
            local inst = CC.new(parent, "bot_min")
            inst:set_geometry(0, 0, 280, 120)

            ----------------------------------------------------------------
            -- Phase 1: bot minimal, health ratio .42, actor.color blue
            ----------------------------------------------------------------
            local bot_valid = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "russian",
                color = {r = 0.35, g = 0.70, b = 0.95},
                health = {current = 42, total = 100, ratio = 0.42,
                          valid = true, provenance = "bot_host"},
                armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }

            _up1 = inst:update(bot_valid, 0)
            _v1 = inst:verify()
            _name1 = inst._name_text:text()
            _peer_dot_v1 = inst._peer_dot:visible()
            _rank_v1 = inst._rank_text:visible()
            _hp_text_v1 = inst._health_text:visible()
            _hp_bg_v1 = inst._hp_bg:visible()
            _hp_fill_v1 = inst._health_fill:visible()
            _ar_bg_v1 = inst._ar_bg:visible()
            _ar_fill_v1 = inst._armor_fill:visible()
            _ar_text_v1 = inst._armor_text:visible()
            _wp_v1 = inst._weapon_text:visible()
            _eq_v1 = inst._equipment_text:visible()
            _cb_v1 = inst._cables_text:visible()
            _pj_v1 = inst._projectile_text:visible()
            _int_v1 = inst._interaction_text:visible()
            _st_v1 = inst._status_text:visible()

            local hp_fill_c1 = inst._health_fill:color()
            _hp_fill_r1 = hp_fill_c1.r
            _hp_fill_g1 = hp_fill_c1.g
            _hp_fill_b1 = hp_fill_c1.b

            local ref_nt = inst._name_text
            local ref_pd = inst._peer_dot
            local ref_rt = inst._rank_text
            local ref_ht = inst._health_text
            local ref_hf = inst._health_fill
            local ref_hbg = inst._hp_bg
            local ref_af = inst._armor_fill
            local ref_at = inst._armor_text
            local ref_ab = inst._ar_bg
            local ref_wt = inst._weapon_text
            local ref_et = inst._equipment_text
            local ref_ct = inst._cables_text
            local ref_pt = inst._projectile_text
            local ref_it = inst._interaction_text
            local ref_st = inst._status_text

            ----------------------------------------------------------------
            -- Phase 2: transition same card -> human full presentation
            ----------------------------------------------------------------
            local human = {
                name = "Tester", level = 10, rank = 2, ai = false,
                peer_id = 1, character_name = "spanish",
                color = {r = 0.2, g = 0.6, b = 1.0},
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
            _name2 = inst._name_text:text()
            _peer_dot_v2 = inst._peer_dot:visible()
            _rank_v2 = inst._rank_text:visible()
            _hp_text_v2 = inst._health_text:visible()
            _hp_bg_v2 = inst._hp_bg:visible()
            _hp_fill_v2 = inst._health_fill:visible()
            _ar_bg_v2 = inst._ar_bg:visible()
            _ar_fill_v2 = inst._armor_fill:visible()
            _ar_text_v2 = inst._armor_text:visible()
            _wp_v2 = inst._weapon_text:visible()
            _eq_v2 = inst._equipment_text:visible()
            _cb_v2 = inst._cables_text:visible()
            _pj_v2 = inst._projectile_text:visible()
            _int_v2 = inst._interaction_text:visible()
            _st_v2 = inst._status_text:visible()

            ----------------------------------------------------------------
            -- Phase 3: transition back -> bot health unknown valid=false
            ----------------------------------------------------------------
            local bot_unk = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "american",
                color = {r = 0.35, g = 0.70, b = 0.95},
                health = {valid = false},
                armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }

            _up3 = inst:update(bot_unk, 2)
            _v3 = inst:verify()
            _name3 = inst._name_text:text()
            _peer_dot_v3 = inst._peer_dot:visible()
            _rank_v3 = inst._rank_text:visible()
            _hp_text_v3 = inst._health_text:visible()
            _hp_bg_v3 = inst._hp_bg:visible()
            _hp_fill_v3 = inst._health_fill:visible()
            _ar_bg_v3 = inst._ar_bg:visible()
            _ar_fill_v3 = inst._armor_fill:visible()
            _ar_text_v3 = inst._armor_text:visible()
            _wp_v3 = inst._weapon_text:visible()
            _eq_v3 = inst._equipment_text:visible()
            _cb_v3 = inst._cables_text:visible()
            _pj_v3 = inst._projectile_text:visible()
            _int_v3 = inst._interaction_text:visible()
            _st_v3 = inst._status_text:visible()

            local hp_fill_w3 = inst._health_fill:w()
            _hp_fill_w3 = hp_fill_w3

            ----------------------------------------------------------------
            -- Primitive identity across all 3 transitions
            ----------------------------------------------------------------
            _same_nt = (inst._name_text == ref_nt)
            _same_pd = (inst._peer_dot == ref_pd)
            _same_rt = (inst._rank_text == ref_rt)
            _same_ht = (inst._health_text == ref_ht)
            _same_hf = (inst._health_fill == ref_hf)
            _same_hbg = (inst._hp_bg == ref_hbg)
            _same_af = (inst._armor_fill == ref_af)
            _same_at = (inst._armor_text == ref_at)
            _same_ab = (inst._ar_bg == ref_ab)
            _same_wt = (inst._weapon_text == ref_wt)
            _same_et = (inst._equipment_text == ref_et)
            _same_ct = (inst._cables_text == ref_ct)
            _same_pt = (inst._projectile_text == ref_pt)
            _same_it = (inst._interaction_text == ref_it)
            _same_st = (inst._status_text == ref_st)

            ----------------------------------------------------------------
            -- Certification: Lua-side loop over weapon_text + health_fill
            -- After bot render, corrupt => verify false, update => verify true,
            -- same object.
            ----------------------------------------------------------------
            local cn = {"wt", "hf"}
            local cp = {"_weapon_text", "_health_fill"}
            for i, pn in ipairs(cp) do
                local prim = inst[pn]
                if pn == "_weapon_text" then
                    prim:set_visible(true)
                else
                    prim:set_color(Color(1, 0, 0))
                end
                _G["cert_" .. cn[i] .. "_bad"] = inst:verify()
                inst:update(bot_unk, 2 + i)
                _G["cert_" .. cn[i] .. "_ok"] = inst:verify()
                _G["cert_" .. cn[i] .. "_same"] = (inst[pn] == prim)
            end

            inst:destroy()
        ''')
        g = lua.globals()

        # Phase 1: bot minimal - name only, no IA suffix, blue health bar
        self.assertTrue(bool(g._up1), "update must succeed for bot with valid health")
        self.assertTrue(bool(g._v1), "verify must be true after bot update")
        self.assertEqual(g._name1, "Dallas",
            "bot name must be localized 'Dallas' WITHOUT 'IA' suffix")
        self.assertFalse(bool(g._peer_dot_v1),
            "bot: _peer_dot must be invisible (no square)")
        self.assertFalse(bool(g._rank_v1),
            "bot: _rank_text must be invisible (no level/rank)")
        self.assertFalse(bool(g._hp_text_v1),
            "bot: _health_text must be invisible (no percentage)")
        self.assertTrue(bool(g._hp_bg_v1),
            "bot: _hp_bg must be visible (health bar background)")
        self.assertTrue(bool(g._hp_fill_v1),
            "bot: _health_fill must be visible (health bar fill)")
        self.assertFalse(bool(g._ar_bg_v1),
            "bot: _ar_bg must be invisible (no armor)")
        self.assertFalse(bool(g._ar_fill_v1),
            "bot: _armor_fill must be invisible (no armor)")
        self.assertFalse(bool(g._ar_text_v1),
            "bot: _armor_text must be invisible (no armor)")
        self.assertFalse(bool(g._wp_v1),
            "bot: _weapon_text must be invisible (no weapon)")
        self.assertFalse(bool(g._eq_v1),
            "bot: _equipment_text must be invisible (no equipment)")
        self.assertFalse(bool(g._cb_v1),
            "bot: _cables_text must be invisible (no cables)")
        self.assertFalse(bool(g._pj_v1),
            "bot: _projectile_text must be invisible (no projectile)")
        self.assertFalse(bool(g._int_v1),
            "bot: _interaction_text must be invisible (no interaction)")
        self.assertFalse(bool(g._st_v1),
            "bot: _status_text must be invisible (no status)")

        # Health fill color must match fixed blue RGB(.35,.70,.95), NOT threshold
        self.assertAlmostEqual(float(g._hp_fill_r1), 0.35, delta=0.02,
            msg="bot health fill color .r must be fixed blue 0.35")
        self.assertAlmostEqual(float(g._hp_fill_g1), 0.70, delta=0.02,
            msg="bot health fill color .g must be fixed blue 0.70")
        self.assertAlmostEqual(float(g._hp_fill_b1), 0.95, delta=0.02,
            msg="bot health fill color .b must be fixed blue 0.95")

        # Phase 2: human transition, full presentation restored
        self.assertTrue(bool(g._up2), "update must succeed for human")
        self.assertTrue(bool(g._v2), "verify must be true for human")
        self.assertEqual(g._name2, "Tester",
            "human name must be plain 'Tester'")
        self.assertTrue(bool(g._peer_dot_v2),
            "human: _peer_dot must be visible (peer marker)")
        self.assertTrue(bool(g._rank_v2),
            "human: _rank_text must be visible (level/rank)")
        self.assertFalse(bool(g._hp_text_v2),
            "human: _health_text must be hidden (no % HP visible)")
        self.assertTrue(bool(g._hp_bg_v2),
            "human: _hp_bg must be visible")
        self.assertTrue(bool(g._hp_fill_v2),
            "human: _health_fill must be visible")
        self.assertTrue(bool(g._ar_bg_v2),
            "human: _ar_bg must be visible (armor)")
        self.assertTrue(bool(g._ar_fill_v2),
            "human: _armor_fill must be visible (armor)")
        self.assertFalse(bool(g._ar_text_v2),
            "human: _armor_text must be hidden (no % armor visible)")
        self.assertTrue(bool(g._wp_v2),
            "human: _weapon_text must be visible (weapon)")
        self.assertTrue(bool(g._eq_v2),
            "human: _equipment_text must be visible (equipment)")
        self.assertTrue(bool(g._cb_v2),
            "human: _cables_text must be visible (cables)")
        self.assertTrue(bool(g._pj_v2),
            "human: _projectile_text must be visible (projectile)")
        self.assertFalse(bool(g._int_v2),
            "human: no interaction row without an active interaction")
        self.assertFalse(bool(g._st_v2),
            "human: no condition row for normal condition")

        # Phase 3: back to bot unknown, no leak, fill width 0
        self.assertTrue(bool(g._up3), "update must succeed for bot unknown")
        self.assertTrue(bool(g._v3), "verify must be true for bot unknown")
        self.assertEqual(g._name3, "Hoxton",
            "bot name must be localized 'Hoxton' (character_name=american)")
        self.assertFalse(bool(g._peer_dot_v3),
            "bot: _peer_dot invisible again (no square)")
        self.assertFalse(bool(g._rank_v3),
            "bot: _rank_text invisible again")
        self.assertFalse(bool(g._hp_text_v3),
            "bot: _health_text invisible again (no percentage)")
        self.assertTrue(bool(g._hp_bg_v3),
            "bot: _hp_bg still visible")
        self.assertTrue(bool(g._hp_fill_v3),
            "bot: _health_fill still visible")
        self.assertFalse(bool(g._ar_bg_v3),
            "bot: _ar_bg invisible again (no armor)")
        self.assertFalse(bool(g._ar_fill_v3),
            "bot: _armor_fill invisible again (no armor)")
        self.assertFalse(bool(g._ar_text_v3),
            "bot: _armor_text invisible again (no armor)")
        self.assertFalse(bool(g._wp_v3),
            "bot: _weapon_text invisible again (no weapon)")
        self.assertFalse(bool(g._eq_v3),
            "bot: _equipment_text invisible again (no equipment)")
        self.assertFalse(bool(g._cb_v3),
            "bot: _cables_text invisible again (no cables)")
        self.assertFalse(bool(g._pj_v3),
            "bot: _projectile_text invisible again (no projectile)")
        self.assertFalse(bool(g._int_v3),
            "bot: _interaction_text invisible again (no interaction)")
        self.assertFalse(bool(g._st_v3),
            "bot: _status_text invisible again (no status)")

        # Unknown health: fill width 0, no invented number
        self.assertAlmostEqual(float(g._hp_fill_w3), 0.0, places=1,
            msg="bot unknown health: fill width must be 0 (no extrapolation)")

        # Primitive identity preserved across all transitions
        for attr in ("_same_nt", "_same_pd", "_same_rt", "_same_ht", "_same_hf",
                      "_same_hbg", "_same_af", "_same_at", "_same_ab", "_same_wt",
                      "_same_et", "_same_ct", "_same_pt", "_same_it", "_same_st"):
            self.assertTrue(bool(g[attr]),
                f"primitive identity preserved: {attr}")

        # Certification: Lua-side loop results
        for prefix in ("cert_wt", "cert_hf"):
            self.assertFalse(bool(g[f"{prefix}_bad"]),
                f"verify false after {prefix} corruption")
            self.assertTrue(bool(g[f"{prefix}_ok"]),
                f"verify true after update repairs {prefix}")
            self.assertTrue(bool(g[f"{prefix}_same"]),
                f"update reuses same {prefix} reference")


if __name__ == "__main__":
    unittest.main()
