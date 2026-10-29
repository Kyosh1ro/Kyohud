"""LOT5 crew roster slice -- published-equipment transition test.

Scope: single test verifying get_crew_snapshot() returns equipment fields
for remote human peers from native synced getters, with detachment and
correct transitions when source data changes.

RED state: equipment collection for crew members does not exist yet.
Tests must fail with explicit messages before nested dereference.
"""
import unittest

from test_hud_actors_crew import _lua


class CrewEquipmentTransitionTests(unittest.TestCase):
    """RED: crew snapshot includes equipment from native synced getters.

    Equipment fields: deployable (id/amount/name_id), cable_ties (amount),
    projectile (id/amount/kind/name_id). Snapshot must be detached; transitions
    must reflect source changes without stale data.
    """

    def test_published_equipment_transition_and_detachment(self):
        """Equipment collected from native synced getters, detached, transitions correctly.

        Setup: remotepeer2 slot2 (no unit, identity may exist without unit),
        AI bot slot3 peer0. managers.player native-shaped _global with
        synced_deployables/synced_cable_ties/synced_grenades for peer_id=2.
        Native getters return these records. Application:digest_value decodes
        digest:1. tweak_data for smoke_screen_grenade (ability) and ammo_bag.

        Seed LOCAL stocks with 999 to detect accidental local reuse; never
        call local getter. refresh_crew(0): human.equipment must have
        deployable={id="ammo_bag",amount=2,name_id="ammo_bag_name"},
        cable_ties={amount=0}, projectile={id="smoke_screen_grenade",amount=1,
        kind="ability",name_id="ability_smoke"}. No max fields invented, no
        second deployable, bot.equipment nil.

        Mutate exported nested deployable.amount/projectile.amount, then
        getter WITHOUT refresh: must return original 2/1 (detachment).

        Replace synced_deployables[2] with {deployable="doctor_bag",amount=0},
        add metadata, refresh_crew(.5): expect new id="doctor_bag", current=0,
        no stale ammo_bag or second inventory entry.

        Remove synced_grenades[2], refresh_crew(1): projectile nil (unknown),
        cable_ties amount=0 retained.

        Explicit fail before nested deref, no production cache injection.
        """
        setup = '''
            -- Peer/session setup
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            -- Remote human peer2 slot2, no unit (identity may exist without unit)
            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            -- AI bot slot3 peer0
            managers.criminals:_set_character(1, {
                name = "russian",
                taken = true,
                unit = nil,
                peer_id = 0,
                data = {ai = true, panel_id = 3},
            })
            -- Remote human slot2
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = nil,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })
            -- Local peer slot4 (excluded from snapshot)
            managers.criminals:_set_character(3, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })

            local mgr = managers.hud
            mgr._teammate_panels = {}
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            -- Native-shaped managers.player with synced equipment getters
            managers.player = managers.player or {}
            managers.player._global = managers.player._global or {}
            managers.player._global.synced_deployables = {
                [2] = {deployable = "ammo_bag", amount = 2}
            }
            managers.player._global.synced_cable_ties = {
                [2] = {amount = 0}
            }
            managers.player._global.synced_grenades = {
                [2] = {grenade = "smoke_screen_grenade", amount = "digest:1"}
            }

            -- Seed LOCAL stocks with 999 to detect accidental local reuse
            managers.player._equipment = {
                selections = {
                    [1] = {equipment = "local_deployable", amount = {"digest:999"}},
                    [2] = {equipment = "local_deployable2", amount = {"digest:999"}}
                },
                selected_index = 1,
                specials = {cable_tie = {amount = "digest:999"}}
            }
            managers.player._global.synced_grenades[1] = {grenade = "local_grenade", amount = "digest:999"}

            -- Native getters
            function managers.player:get_synced_deployable_equipment(peer_id)
                return self._global.synced_deployables[peer_id]
            end
            function managers.player:get_synced_cable_ties(peer_id)
                return self._global.synced_cable_ties[peer_id]
            end
            function managers.player:get_synced_grenades(peer_id)
                return self._global.synced_grenades[peer_id]
            end

            -- Application:digest_value native-shaped decode
            Application = Application or {}
            _digest_decode_seen = false
            function Application:digest_value(v, encode)
                assert(encode == false)
                if type(v) == "string" and v:sub(1, 7) == "digest:" then
                    _digest_decode_seen = true
                    return tonumber(v:sub(8))
                end
                return nil
            end

            -- tweak_data for projectiles and equipments
            tweak_data = tweak_data or {}
            tweak_data.blackmarket = tweak_data.blackmarket or {}
            tweak_data.blackmarket.projectiles = tweak_data.blackmarket.projectiles or {}
            tweak_data.blackmarket.projectiles.smoke_screen_grenade = {
                ability = true,
                name_id = "ability_smoke"
            }
            tweak_data.equipments = tweak_data.equipments or {}
            tweak_data.equipments.ammo_bag = {text_id = "ammo_bag_name"}
            tweak_data.equipments.doctor_bag = {text_id = "doctor_bag_name"}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"
                return
            end
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            _api_missing = false

            -- Initial refresh at t=0
            ACT:refresh_crew(managers.hud, 0)
            local snap0 = ACT:get_crew_snapshot()

            -- Find human entry (peer_id=2) and bot entry (ai=true)
            _human0 = nil
            _bot0 = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then _human0 = e end
                if e.ai == true and e.peer_id == nil then _bot0 = e end
            end

            -- Extract equipment fields from human
            _human_eq0 = _human0 and _human0.equipment or nil
            _human_deploy0 = _human_eq0 and _human_eq0.deployable or nil
            _human_cable0 = _human_eq0 and _human_eq0.cable_ties or nil
            _human_proj0 = _human_eq0 and _human_eq0.projectile or nil

            -- Check bot has no equipment
            _bot_eq0 = _bot0 and _bot0.equipment or nil

            -- Capture original scalars before mutation
            _human_deploy0_amount = _human_deploy0 and _human_deploy0.amount or nil
            _human_proj0_amount = _human_proj0 and _human_proj0.amount or nil
            _human_deploy0_max = _human_deploy0 and _human_deploy0.max or nil
            _human_proj0_max = _human_proj0 and _human_proj0.max or nil

            -- Test detachment: mutate exported nested fields
            if _human_deploy0 then
                _human_deploy0.amount = 9999
            end
            if _human_proj0 then
                _human_proj0.amount = 9999
            end

            -- Getter WITHOUT refresh must return original values
            local snap0b = ACT:get_crew_snapshot()
            _human0b = nil
            for _, e in ipairs(snap0b) do
                if e.peer_id == 2 then _human0b = e end
            end
            _human_eq0b = _human0b and _human0b.equipment or nil
            _human_deploy0b_amt = _human_eq0b and _human_eq0b.deployable
                and _human_eq0b.deployable.amount or nil
            _human_proj0b_amt = _human_eq0b and _human_eq0b.projectile
                and _human_eq0b.projectile.amount or nil

            -- Transition: replace synced_deployables[2]
            managers.player._global.synced_deployables[2] = {
                deployable = "doctor_bag",
                amount = 0,
                _metadata = "test"
            }

            ACT:refresh_crew(managers.hud, 0.5)
            local snap1 = ACT:get_crew_snapshot()
            _human1 = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then _human1 = e end
            end
            _human_eq1 = _human1 and _human1.equipment or nil
            _human_deploy1 = _human_eq1 and _human_eq1.deployable or nil

            -- Count deployables (should be exactly 1)
            _deploy_count1 = 0
            if _human_eq1 then
                for _ in pairs(_human_eq1.deployables or {}) do
                    _deploy_count1 = _deploy_count1 + 1
                end
            end

            -- Transition: remove synced_grenades[2]
            managers.player._global.synced_grenades[2] = nil

            ACT:refresh_crew(managers.hud, 1.0)
            local snap2 = ACT:get_crew_snapshot()
            _human2 = nil
            for _, e in ipairs(snap2) do
                if e.peer_id == 2 then _human2 = e end
            end
            _human_eq2 = _human2 and _human2.equipment or nil
            _human_proj2 = _human_eq2 and _human_eq2.projectile or nil
            _human_cable2 = _human_eq2 and _human_eq2.cable_ties or nil
        ''')
        g = lua.globals()

        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        # Verify human and bot found
        self.assertIsNotNone(g._human0,
            "RED: snapshot must include remote human (peer_id=2)")
        self.assertIsNotNone(g._bot0,
            "RED: snapshot must include AI bot")

        # Verify human equipment exists
        self.assertIsNotNone(g._human_eq0,
            "RED: human.equipment must exist after refresh_crew(0)")

        # Verify deployable
        self.assertIsNotNone(g._human_deploy0,
            "RED: human.equipment.deployable must exist")
        if g._human_deploy0:
            self.assertEqual(g._human_deploy0.id, "ammo_bag",
                "RED: deployable.id must be 'ammo_bag'")
            self.assertEqual(float(g._human_deploy0_amount), 2.0,
                "RED: deployable.amount must be 2 (captured before mutation)")
            self.assertEqual(g._human_deploy0.name_id, "ammo_bag_name",
                "RED: deployable.name_id must come from tweak_data.equipments.ammo_bag.text_id")
            self.assertIsNone(g._human_deploy0_max,
                "RED: deployable must not have a max field")

        # Verify cable_ties
        self.assertIsNotNone(g._human_cable0,
            "RED: human.equipment.cable_ties must exist")
        if g._human_cable0:
            self.assertEqual(float(g._human_cable0.amount), 0.0,
                "RED: cable_ties.amount must be 0")

        # Verify projectile
        self.assertIsNotNone(g._human_proj0,
            "RED: human.equipment.projectile must exist")
        if g._human_proj0:
            self.assertEqual(g._human_proj0.id, "smoke_screen_grenade",
                "RED: projectile.id must be 'smoke_screen_grenade'")
            self.assertEqual(float(g._human_proj0_amount), 1.0,
                "RED: projectile.amount must be 1 (captured before mutation)")
            self.assertEqual(g._human_proj0.kind, "ability",
                "RED: projectile.kind must be 'ability' (tweak_data.blackmarket.projectiles.smoke_screen_grenade.ability=true)")
            self.assertEqual(g._human_proj0.name_id, "ability_smoke",
                "RED: projectile.name_id must come from tweak_data.blackmarket.projectiles.smoke_screen_grenade.name_id")
            self.assertIsNone(g._human_proj0_max,
                "RED: projectile must not have a max field")

        # Verify bot has no equipment
        self.assertIsNone(g._bot_eq0,
            "RED: bot.equipment must be nil (equipment only for humans)")

        # Verify detachment: mutation must not affect internal state
        self.assertEqual(float(g._human_deploy0b_amt), 2.0,
            "RED: deployable.amount must remain 2 after exported mutation (detachment)")
        self.assertEqual(float(g._human_proj0b_amt), 1.0,
            "RED: projectile.amount must remain 1 after exported mutation (detachment)")
        self.assertTrue(g._digest_decode_seen,
            "RED: Application:digest_value must have been called with encode=false and returned decoded number")

        # Verify transition: new deployable
        self.assertIsNotNone(g._human_deploy1,
            "RED: human.equipment.deployable must exist after transition")
        if g._human_deploy1:
            self.assertEqual(g._human_deploy1.id, "doctor_bag",
                "RED: deployable.id must be 'doctor_bag' after replacement")
            self.assertEqual(float(g._human_deploy1.amount), 0.0,
                "RED: deployable.amount must be 0 after replacement")
            self.assertEqual(g._human_deploy1.name_id, "doctor_bag_name",
                "RED: deployable.name_id must come from tweak_data.equipments.doctor_bag.text_id")

        # Verify no stale ammo_bag or second deployable
        self.assertEqual(float(g._deploy_count1), 0.0,
            "RED: no second deployable entry (deployables table should be empty or absent)")

        # Verify projectile nil after removal
        self.assertIsNone(g._human_proj2,
            "RED: projectile must be nil after synced_grenades[2] removal (unknown)")

        # Verify cable_ties retained
        self.assertIsNotNone(g._human_cable2,
            "RED: cable_ties must be retained after grenade removal")
        if g._human_cable2:
            self.assertEqual(float(g._human_cable2.amount), 0.0,
                "RED: cable_ties.amount must remain 0 after grenade removal")


if __name__ == "__main__":
    unittest.main()
