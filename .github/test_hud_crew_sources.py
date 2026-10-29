"""LOT5 crew roster network sources -- health/armor via registered posthooks only.

Scope: single test verifying get_crew_snapshot()[1] exposes health/armor tables
with current/total/ratio/valid/provenance="network_quantized", and that native
panel preseeded data is NOT scraped. Snapshot must be detached (mutations do
not affect subsequent getters). Zero current is valid=true, distinct from nil
unknown.
"""
from pathlib import Path
import sys
import unittest

from lupa.luajit21 import LuaRuntime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hud_actors import NATIVE_HEALTH_ARMOR_FIXTURE, NATIVE_REVIVES_CONDITION_FIXTURE
from test_hud_actors_crew import _lua


class CrewNetworkHealthArmorTests(unittest.TestCase):
    """RED: network health/armor detached snapshot, zero valid.

    Setup: remote peer2 in slot 2, criminals record peer_id=2 panel_id=2,
    HUD panel _peer_id=2/_ai=false, local peer excluded. Preseed native
    panel.health_data/armor_data with 100/100 but do NOT dispatch through
    posthooks. refresh_crew(mgr, 0) must see roster entry but health/armor
    nil (unobserved native cache must NOT be scraped).

    Dispatch health 25/100 and armor 80/200 via registered posthooks. Assert
    get_crew_snapshot()[1] has health/armor tables with current/total/ratio
    .25/.4, valid=true, provenance="network_quantized". Optional revives 3
    and condition mugshot_downed captured.

    Mutate returned snapshot health.current/ratio and armor.total, get again
    WITHOUT refresh, assert original values unchanged (deep copy).

    Dispatch health 0/100, assert current=0, ratio=0, valid=true (distinct
    from nil unknown).
    """

    def test_network_health_armor_detached_and_zero_valid(self):
        setup = NATIVE_HEALTH_ARMOR_FIXTURE + NATIVE_REVIVES_CONDITION_FIXTURE + r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = nil,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })

            local mgr = managers.hud
            mgr._teammate_panels[2] = {
                _peer_id = 2,
                _ai = false,
            }
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            mgr:set_teammate_health(2, {current = 100, total = 100})
            mgr:set_teammate_armor(2, {current = 100, total = 100})
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

            local mgr = managers.hud
            ACT:refresh_crew(mgr, 0)

            local snap0 = ACT:get_crew_snapshot()
            _snap0_len = #snap0
            _snap0_1 = snap0[1]
            _snap0_1_has_health = _snap0_1 and _snap0_1.health ~= nil
            _snap0_1_has_armor = _snap0_1 and _snap0_1.armor ~= nil

            local function dispatch_health(panel_id, data)
                mgr:set_teammate_health(panel_id, data)
                for _, e in ipairs(Hooks._all) do
                    if e.method == "set_teammate_health" then
                        e.fn(mgr, panel_id, data)
                    end
                end
            end

            local function dispatch_armor(panel_id, data)
                mgr:set_teammate_armor(panel_id, data)
                for _, e in ipairs(Hooks._all) do
                    if e.method == "set_teammate_armor" then
                        e.fn(mgr, panel_id, data)
                    end
                end
            end

            local function dispatch_revives(panel_id, amount)
                mgr:set_teammate_revives(panel_id, amount)
                for _, e in ipairs(Hooks._all) do
                    if e.method == "set_teammate_revives" then
                        e.fn(mgr, panel_id, amount)
                    end
                end
            end

            local function dispatch_condition(panel_id, icon, text)
                mgr:set_teammate_condition(panel_id, icon, text)
                for _, e in ipairs(Hooks._all) do
                    if e.method == "set_teammate_condition" then
                        e.fn(mgr, panel_id, icon, text)
                    end
                end
            end

            dispatch_health(2, {current = 25, total = 100})
            dispatch_armor(2, {current = 80, total = 200})
            dispatch_revives(2, 3)
            dispatch_condition(2, "mugshot_downed", "Downed")

            local snap1 = ACT:get_crew_snapshot()
            _snap1_len = #snap1
            local entry = snap1[1]
            _entry_peer_id = entry and entry.peer_id
            _hp_cur = entry and entry.health and entry.health.current
            _hp_tot = entry and entry.health and entry.health.total
            _hp_rat = entry and entry.health and entry.health.ratio
            _hp_val = entry and entry.health and entry.health.valid
            _hp_prov = entry and entry.health and entry.health.provenance
            _ar_cur = entry and entry.armor and entry.armor.current
            _ar_tot = entry and entry.armor and entry.armor.total
            _ar_rat = entry and entry.armor and entry.armor.ratio
            _ar_val = entry and entry.armor and entry.armor.valid
            _ar_prov = entry and entry.armor and entry.armor.provenance
            _downs = entry and entry.downs
            _cond_icon = entry and entry.condition_icon
            _entry = entry
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._snap0_len), 1.0,
            "RED: pre-dispatch snapshot must have 1 entry (remote peer2)")
        self.assertIs(g._snap0_1_has_health, False,
            "RED: pre-dispatch health must be nil (native preseed must NOT be scraped)")
        self.assertIs(g._snap0_1_has_armor, False,
            "RED: pre-dispatch armor must be nil (native preseed must NOT be scraped)")

        self.assertEqual(float(g._snap1_len), 1.0,
            "RED: post-dispatch snapshot must have 1 entry")
        self.assertEqual(float(g._entry_peer_id), 2.0,
            "RED: snapshot[1] must be peer2")

        self.assertIsNotNone(g._hp_cur,
            "RED: explicit missing crew health")
        self.assertIsNotNone(g._ar_cur,
            "RED: explicit missing crew armor")

        self.assertEqual(float(g._hp_cur), 25.0,
            "RED: health.current must be 25")
        self.assertEqual(float(g._hp_tot), 100.0,
            "RED: health.total must be 100")
        self.assertAlmostEqual(float(g._hp_rat), 0.25, places=5,
            msg="RED: health.ratio must be 0.25 (25/100)")
        self.assertIs(g._hp_val, True,
            "RED: health must be valid=true")
        self.assertEqual(g._hp_prov, "network_quantized",
            "RED: health.provenance must be 'network_quantized'")

        self.assertEqual(float(g._ar_cur), 80.0,
            "RED: armor.current must be 80")
        self.assertEqual(float(g._ar_tot), 200.0,
            "RED: armor.total must be 200")
        self.assertAlmostEqual(float(g._ar_rat), 0.4, places=5,
            msg="RED: armor.ratio must be 0.4 (80/200)")
        self.assertIs(g._ar_val, True,
            "RED: armor must be valid=true")
        self.assertEqual(g._ar_prov, "network_quantized",
            "RED: armor.provenance must be 'network_quantized'")

        self.assertEqual(float(g._downs), 2.0,
            "RED: downs must be 2 (max(3-1,0))")
        self.assertEqual(g._cond_icon, "mugshot_downed",
            "RED: condition_icon must be 'mugshot_downed'")

        lua.execute('''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud
            local entry = _entry

            entry.health.current = 999
            entry.health.ratio = 999
            entry.armor.total = 999

            local snap2 = ACT:get_crew_snapshot()
            local entry2 = snap2[1]
            _snap2_hp_cur = entry2 and entry2.health and entry2.health.current
            _snap2_hp_rat = entry2 and entry2.health and entry2.health.ratio
            _snap2_ar_tot = entry2 and entry2.armor and entry2.armor.total

            mgr:set_teammate_health(2, {current = 0, total = 100})
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, {current = 0, total = 100})
                end
            end

            local snap3 = ACT:get_crew_snapshot()
            local entry3 = snap3[1]
            _snap3_hp_cur = entry3 and entry3.health and entry3.health.current
            _snap3_hp_rat = entry3 and entry3.health and entry3.health.ratio
            _snap3_hp_val = entry3 and entry3.health and entry3.health.valid
        ''')
        g = lua.globals()

        self.assertEqual(float(g._snap2_hp_cur), 25.0,
            "RED: snapshot must be detached (health.current unchanged after mutation)")
        self.assertAlmostEqual(float(g._snap2_hp_rat), 0.25, places=5,
            msg="RED: snapshot must be detached (health.ratio unchanged after mutation)")
        self.assertEqual(float(g._snap2_ar_tot), 200.0,
            "RED: snapshot must be detached (armor.total unchanged after mutation)")

        self.assertEqual(float(g._snap3_hp_cur), 0.0,
            "RED: zero current must be captured as 0")
        self.assertAlmostEqual(float(g._snap3_hp_rat), 0.0, places=5,
            msg="RED: 0/100 ratio must be 0")
        self.assertIs(g._snap3_hp_val, True,
            "RED: zero current with valid total must be valid=true (distinct from nil unknown)")

    def test_condition_revives_independent_of_health_armor(self):
        setup = NATIVE_HEALTH_ARMOR_FIXTURE + NATIVE_REVIVES_CONDITION_FIXTURE + r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = nil,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })

            local mgr = managers.hud
            mgr._teammate_panels[2] = {
                _peer_id = 2,
                _ai = false,
            }
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            mgr:set_teammate_health(2, {current = 100, total = 100})
            mgr:set_teammate_armor(2, {current = 100, total = 100})
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

            local mgr = managers.hud
            ACT:refresh_crew(mgr, 0)

            local function dispatch_revives(panel_id, amount)
                mgr:set_teammate_revives(panel_id, amount)
                for _, e in ipairs(Hooks._all) do
                    if e.method == "set_teammate_revives" then
                        e.fn(mgr, panel_id, amount)
                    end
                end
            end

            local function dispatch_condition(panel_id, icon, text)
                mgr:set_teammate_condition(panel_id, icon, text)
                for _, e in ipairs(Hooks._all) do
                    if e.method == "set_teammate_condition" then
                        e.fn(mgr, panel_id, icon, text)
                    end
                end
            end

            dispatch_revives(2, 3)
            dispatch_condition(2, "mugshot_custody", "In custody")

            local snap = ACT:get_crew_snapshot()
            _snap_len = #snap
            local entry = snap[1]
            _entry_peer_id = entry and entry.peer_id
            _has_health = entry and entry.health ~= nil
            _has_armor = entry and entry.armor ~= nil
            _downs = entry and entry.downs
            _revives = entry and entry.revives
            _cond_icon = entry and entry.condition_icon
            _cond_text = entry and entry.condition_text
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._snap_len), 1.0,
            "REGRESSION: snapshot must have 1 entry (remote peer2)")
        self.assertEqual(float(g._entry_peer_id), 2.0,
            "REGRESSION: snapshot[1] must be peer2")
        self.assertIs(g._has_health, False,
            "REGRESSION: health must be nil when no health dispatched")
        self.assertIs(g._has_armor, False,
            "REGRESSION: armor must be nil when no armor dispatched")
        self.assertEqual(float(g._revives), 3.0,
            "REGRESSION: revives must be 3 without health/armor gate")
        self.assertEqual(float(g._downs), 2.0,
            "REGRESSION: downs must be 2 (max(3-1,0)) without health/armor gate")
        self.assertEqual(g._cond_icon, "mugshot_custody",
            "REGRESSION: condition_icon must be 'mugshot_custody' without health/armor gate")
        self.assertEqual(g._cond_text, "In custody",
            "REGRESSION: condition_text must be exactly 'In custody' as published")


class CrewBotSourceTransitionTests(unittest.TestCase):
    """RED: bot host -> bleedout -> client transition, ratio-only, no current/total.

    Native verified API: unit:character_damage(), cd:health_ratio() returns _health_ratio;
    cd:bleed_out() returns _bleed_out; cd:fatal() returns _fatal; cd:dead() returns _dead;
    cd:arrested() returns _arrested_timer (nil normally). Network:is_server() qualifies host.
    """

    def test_bot_host_bleedout_client_transition(self):
        """Bot host ratio .65 -> bleedout ratio 1 -> client: health/bleedout nil, phase kept.

        Build native-shaped fixture ONE bot ai=true peer_id=0 slot=2 with alive unit,
        cd getters, live local peer for roster. Server=true initial _health_ratio=.65,
        no bleedout/fatal/dead/arrested; refresh_crew0 snapshot bot.health must have
        ratio .65, valid=true, provenance="bot_host"; armor/downs/level/rank nil.

        Mutate returned bot health ratio then getter WITHOUT refresh ensuring detachment
        before transition.

        Set cd._bleed_out=true, _health_ratio=1; refresh_crew(mgr, 0.5) must have
        health=nil and separate bleedout table ratio=1, valid=true, provenance=bot_host,
        phase="bleedout" (not normal health=100).

        Set Network server false; refresh_crew(mgr, 1) MUST have health nil and bleedout
        nil (inherited ratio not certified client), phase still bleedout from state
        getter. Assert client poll did NOT call health_ratio by call counter (only state
        gets valid); host did. No HUD metric callback for bots, no fake unit health.
        Do not require numeric current/total for ratio-only bot data.
        """
        setup = r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            _cd_calls = 0
            cd = {
                _health_ratio = 0.65,
                _bleed_out = false,
                _fatal = false,
                _dead = false,
                _arrested_timer = nil,
                health_ratio = function(self)
                    _cd_calls = _cd_calls + 1
                    return self._health_ratio
                end,
                bleed_out = function(self) return self._bleed_out end,
                fatal = function(self) return self._fatal end,
                dead = function(self) return self._dead end,
                arrested = function(self) return self._arrested_timer end,
            }
            bot_unit = {
                _alive = true,
                character_damage = function(self) return cd end,
            }

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 1},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = bot_unit,
                peer_id = 0,
                data = {ai = true, panel_id = 2},
            })

            local mgr = managers.hud
            mgr._teammate_panels[2] = {
                _peer_id = 0,
                _ai = true,
            }
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            Network = {
                _is_server = true,
                is_server = function(self) return self._is_server end,
                is_client = function(self) return not self._is_server end,
            }
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

            local mgr = managers.hud
            ACT:refresh_crew(mgr, 0)
            local snap0 = ACT:get_crew_snapshot()

            _bot = nil
            for _, e in ipairs(snap0) do
                if e.ai == true then _bot = e; break end
            end
            _snap0_len = #snap0
            _has_bot = _bot ~= nil
            if _bot then
                _bot_health = _bot.health
                _bot_armor = _bot.armor
                _bot_downs = _bot.downs
                _bot_level = _bot.level
                _bot_rank = _bot.rank
                _bot_peer_id = _bot.peer_id
                _bot_hp_ratio = _bot.health and _bot.health.ratio
                _bot_hp_valid = _bot.health and _bot.health.valid
                _bot_hp_prov = _bot.health and _bot.health.provenance
            end
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._snap0_len), 1.0,
            "RED: must have 1 bot entry")
        self.assertTrue(bool(g._has_bot),
            "RED: bot entry must exist in snapshot")
        self.assertIsNotNone(g._bot_health,
            "RED: bot.health must be present on host")
        self.assertIs(g._bot_armor, None,
            "RED: bot.armor must be nil")
        self.assertIsNone(g._bot_downs,
            "RED: bot.downs must be nil")
        self.assertIsNone(g._bot_level,
            "RED: bot.level must be nil")
        self.assertIsNone(g._bot_rank,
            "RED: bot.rank must be nil")
        self.assertAlmostEqual(float(g._bot_hp_ratio), 0.65, places=5,
            msg="RED: bot health.ratio must be 0.65")
        self.assertIs(g._bot_hp_valid, True,
            "RED: bot health.valid must be true")
        self.assertEqual(g._bot_hp_prov, "bot_host",
            "RED: bot health.provenance must be 'bot_host'")
        self.assertIsNone(g._bot_peer_id,
            "RED: bot peer_id must be nil (source sentinel 0 not exported)")

        lua.execute('''
            local ACT = kyohud.hud.actors
            local snap0 = ACT:get_crew_snapshot()
            local bot0 = nil
            for _, e in ipairs(snap0) do
                if e.ai == true then bot0 = e; break end
            end
            if bot0 and bot0.health then
                bot0.health.ratio = 999
            end
            local snap_detach = ACT:get_crew_snapshot()
            local bot_detach = nil
            for _, e in ipairs(snap_detach) do
                if e.ai == true then bot_detach = e; break end
            end
            _detached_ratio = bot_detach and bot_detach.health
                and bot_detach.health.ratio
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._detached_ratio), 0.65, places=5,
            msg="RED: snapshot must be detached (ratio unchanged after mutation)")

        lua.execute('''
            local ACT = kyohud.hud.actors
            cd._bleed_out = true
            cd._health_ratio = 1
            _calls_before_bleedout = _cd_calls

            local mgr = managers.hud
            ACT:refresh_crew(mgr, 0.5)
            local snap_bo = ACT:get_crew_snapshot()
            local bot_bo = nil
            for _, e in ipairs(snap_bo) do
                if e.ai == true then bot_bo = e; break end
            end
            _bot_bo_health = bot_bo and bot_bo.health
            _bot_bo_bleedout = bot_bo and bot_bo.bleedout
            _bot_bo_ratio = bot_bo and bot_bo.bleedout
                and bot_bo.bleedout.ratio
            _bot_bo_valid = bot_bo and bot_bo.bleedout
                and bot_bo.bleedout.valid
            _bot_bo_prov = bot_bo and bot_bo.bleedout
                and bot_bo.bleedout.provenance
            _bot_bo_phase = bot_bo and bot_bo.phase
            _calls_after_bleedout = _cd_calls
        ''')
        g = lua.globals()
        self.assertIsNone(g._bot_bo_health,
            "RED: in bleedout, bot.health must be nil")
        self.assertIsNotNone(g._bot_bo_bleedout,
            "RED: bot.bleedout must be present")
        self.assertAlmostEqual(float(g._bot_bo_ratio), 1.0, places=5,
            msg="RED: bleedout.ratio must be 1")
        self.assertIs(g._bot_bo_valid, True,
            "RED: bleedout.valid must be true")
        self.assertEqual(g._bot_bo_prov, "bot_host",
            "RED: bleedout.provenance must be 'bot_host'")
        self.assertEqual(g._bot_bo_phase, "bleedout",
            "RED: bleedout.phase must be 'bleedout'")
        self.assertGreater(float(g._calls_after_bleedout),
            float(g._calls_before_bleedout),
            "RED: host poll must call health_ratio")

        lua.execute('''
            local ACT = kyohud.hud.actors
            Network._is_server = false
            _calls_before_client = _cd_calls

            local mgr = managers.hud
            ACT:refresh_crew(mgr, 1)
            local snap_cl = ACT:get_crew_snapshot()
            local bot_cl = nil
            for _, e in ipairs(snap_cl) do
                if e.ai == true then bot_cl = e; break end
            end
            _bot_cl_health = bot_cl and bot_cl.health
            _bot_cl_bleedout = bot_cl and bot_cl.bleedout
            _bot_cl_phase = bot_cl and bot_cl.phase
            _calls_after_client = _cd_calls
        ''')
        g = lua.globals()
        self.assertIsNone(g._bot_cl_health,
            "RED: as client, bot.health must be nil")
        self.assertIsNone(g._bot_cl_bleedout,
            "RED: as client, bot.bleedout must be nil "
            "(inherited ratio not certified)")
        self.assertEqual(g._bot_cl_phase, "bleedout",
            "RED: phase must still be 'bleedout' from state getter")
        self.assertEqual(float(g._calls_before_client),
            float(g._calls_after_client),
            "RED: client poll must NOT call health_ratio")

    def test_bot_host_userdata_network_accepts_callable_methods(self):
        """Network is userdata with callable methods, not table.

        Production currently rejects because type(Network) ~= "table" despite
        Network:is_server() being callable. LuaJIT 2.1 SOL allows userdata with
        __index metatable for method lookup. Verify type(Network) == "userdata",
        then assert bot.health.ratio=0.65, valid=true, provenance="bot_host",
        and health_ratio called exactly 1 time.
        """
        setup = r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            _cd_calls = 0
            cd = {
                _health_ratio = 0.65,
                _bleed_out = false,
                _fatal = false,
                _dead = false,
                _arrested_timer = nil,
                health_ratio = function(self)
                    _cd_calls = _cd_calls + 1
                    return self._health_ratio
                end,
                bleed_out = function(self) return self._bleed_out end,
                fatal = function(self) return self._fatal end,
                dead = function(self) return self._dead end,
                arrested = function(self) return self._arrested_timer end,
            }
            bot_unit = {
                _alive = true,
                character_damage = function(self) return cd end,
            }

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 1},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = bot_unit,
                peer_id = 0,
                data = {ai = true, panel_id = 2},
            })

            local mgr = managers.hud
            mgr._teammate_panels[2] = {
                _peer_id = 0,
                _ai = true,
            }
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            Network = newproxy(true)
            getmetatable(Network).__index = {
                is_server = function(self) return true end,
                is_client = function(self) return false end,
            }
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

            _network_type = type(Network)

            local mgr = managers.hud
            ACT:refresh_crew(mgr, 0)
            local snap0 = ACT:get_crew_snapshot()

            _bot = nil
            for _, e in ipairs(snap0) do
                if e.ai == true then _bot = e; break end
            end
            _has_bot = _bot ~= nil
            if _bot then
                _bot_hp_ratio = _bot.health and _bot.health.ratio
                _bot_hp_valid = _bot.health and _bot.health.valid
                _bot_hp_prov = _bot.health and _bot.health.provenance
            end
            _calls_after = _cd_calls
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(g._network_type, "userdata",
            "RED: Network must be userdata, not table")
        self.assertTrue(bool(g._has_bot),
            "RED: bot entry must exist in snapshot")
        self.assertIsNotNone(g._bot_hp_ratio,
            "REGRESSION: bot.health must be present on host (userdata Network)")
        self.assertAlmostEqual(float(g._bot_hp_ratio), 0.65, places=5,
            msg="REGRESSION: bot health.ratio must be 0.65 (userdata Network)")
        self.assertIs(g._bot_hp_valid, True,
            "REGRESSION: bot health.valid must be true (userdata Network)")
        self.assertEqual(g._bot_hp_prov, "bot_host",
            "REGRESSION: bot health.provenance must be 'bot_host' (userdata Network)")
        self.assertEqual(float(g._calls_after), 1.0,
            "REGRESSION: health_ratio must be called exactly once")


class CrewCallsignColorTests(unittest.TestCase):
    """RED: callsign color from chat_colors userdata, detached snapshot, posthook update.

    Setup: local peer1 excluded, human peer2 slot1 ai=false, bot slot2 ai=true peer_id=0.
    tweak_data.chat_colors = 5 Color userdata. Human uses color2 (id=peer_id=2),
    bot uses color5 (id=max_players+1=5). Snapshot exports color as table {r,g,b,a=1},
    not userdata alias. Posthook set_teammate_callsign(1,3) updates human immediately
    without refresh. Out-of-range id=99 falls back to last color.
    """

    def test_callsign_color_human_bot_detached_and_posthook(self):
        """Human/bot callsign colors from native userdata, detached, posthook immediate.

        Setup live localpeer1; humanpeer2 slot1, bot peer_id0 ai=true slot2. tweak_data.max_players=4
        and chat_colors dense five userdata via newproxy(true) with .r/.g/.b/.a fields __index;
        human color2 rgb .2,.4,.6; bot color5 .8,.3,.1, .a=.37 (native alpha not copied into owned
        opacity). refresh_crew0 snapshot entries color tables r/g/b corresponding, a=1; no Color
        userdata alias in exported snapshot. Mutate human returned color.r and get again WITHOUT
        refresh ensure detached. Define native HUDManager:set_teammate_callsign(i,id) BEFORE actors
        load (record call only). Dispatch real registered posthook set_teammate_callsign(1,3);
        color3 rgb .1,.9,.5 must show immediately without refresh for human, bot unchanged. Then
        event id99 resolves last color5 fallback. No scans in getter, no production/cache injection.
        """
        setup = r'''
            -- Native Color userdata factory
            local function make_color(r, g, b, a)
                local proxy = newproxy(true)
                local mt = getmetatable(proxy)
                mt.__index = {
                    r = r,
                    g = g,
                    b = b,
                    a = a,
                }
                return proxy
            end

            -- tweak_data setup
            tweak_data = tweak_data or {}
            tweak_data.max_players = 4
            tweak_data.chat_colors = {
                make_color(0.1, 0.2, 0.3, 1.0),  -- color1
                make_color(0.2, 0.4, 0.6, 1.0),  -- color2 (human)
                make_color(0.1, 0.9, 0.5, 1.0),  -- color3 (posthook update)
                make_color(0.5, 0.5, 0.5, 1.0),  -- color4
                make_color(0.8, 0.3, 0.1, 0.37), -- color5 (bot, fallback)
            }

            -- Native set_teammate_callsign stub (record call only)
            _callsign_calls = {}
            function HUDManager:set_teammate_callsign(i, id)
                table.insert(_callsign_calls, {i = i, id = id})
                if not self._teammate_panels[i] then
                    self._teammate_panels[i] = {}
                end
                self._teammate_panels[i].callsign_id = id
            end

            -- Session/peer setup
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            -- Criminals setup
            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = nil,
                peer_id = 2,
                data = {ai = false, panel_id = 1},
            })
            managers.criminals:_set_character(3, {
                name = "russian",
                taken = true,
                unit = nil,
                peer_id = 0,
                data = {ai = true, panel_id = 2},
            })

            -- HUD panels setup
            local mgr = managers.hud
            mgr._teammate_panels[1] = {
                _peer_id = 2,
                _ai = false,
            }
            mgr._teammate_panels[2] = {
                _peer_id = 0,
                _ai = true,
            }
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            -- Dispatch initial callsign setup (simulating native add_teammate_panel)
            -- Human slot1: id = peer_id = 2
            mgr:set_teammate_callsign(1, 2)
            -- Bot slot2: id = max_players+1 = 5
            mgr:set_teammate_callsign(2, 5)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        # Dispatch posthooks for initial callsign setup
        lua.execute('''
            local mgr = managers.hud
            for _, call in ipairs(_callsign_calls) do
                for _, e in ipairs(Hooks._all) do
                    if e.method == "set_teammate_callsign" then
                        e.fn(mgr, call.i, call.id)
                    end
                end
            end
        ''')

        # Test 1: refresh_crew snapshot has colors
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

            local mgr = managers.hud
            ACT:refresh_crew(mgr, 0)
            local snap0 = ACT:get_crew_snapshot()

            _snap0_len = #snap0

            -- Find human (peer_id=2) and bot (ai=true)
            _human = nil
            _bot = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then _human = e end
                if e.ai == true then _bot = e end
            end

            _has_human = _human ~= nil
            _has_bot = _bot ~= nil

            -- Extract colors
            _human_color = _human and _human.color
            _bot_color = _bot and _bot.color

            _human_color_type = type(_human_color)
            _bot_color_type = type(_bot_color)

            _human_r = _human_color and _human_color.r
            _human_g = _human_color and _human_color.g
            _human_b = _human_color and _human_color.b
            _human_a = _human_color and _human_color.a

            _bot_r = _bot_color and _bot_color.r
            _bot_g = _bot_color and _bot_color.g
            _bot_b = _bot_color and _bot_color.b
            _bot_a = _bot_color and _bot_color.a
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._snap0_len), 2.0,
            "RED: snapshot must have 2 entries (human + bot)")
        self.assertTrue(bool(g._has_human),
            "RED: snapshot must include human (peer_id=2)")
        self.assertTrue(bool(g._has_bot),
            "RED: snapshot must include bot (ai=true)")

        self.assertEqual(g._human_color_type, "table",
            "RED: human.color must be a table, not userdata")
        self.assertEqual(g._bot_color_type, "table",
            "RED: bot.color must be a table, not userdata")

        self.assertAlmostEqual(float(g._human_r), 0.2, places=5,
            msg="RED: human.color.r must be 0.2 (color2)")
        self.assertAlmostEqual(float(g._human_g), 0.4, places=5,
            msg="RED: human.color.g must be 0.4 (color2)")
        self.assertAlmostEqual(float(g._human_b), 0.6, places=5,
            msg="RED: human.color.b must be 0.6 (color2)")
        self.assertAlmostEqual(float(g._human_a), 1.0, places=5,
            msg="RED: human.color.a must be 1 (native alpha not copied)")

        self.assertAlmostEqual(float(g._bot_r), 0.8, places=5,
            msg="RED: bot.color.r must be 0.8 (color5)")
        self.assertAlmostEqual(float(g._bot_g), 0.3, places=5,
            msg="RED: bot.color.g must be 0.3 (color5)")
        self.assertAlmostEqual(float(g._bot_b), 0.1, places=5,
            msg="RED: bot.color.b must be 0.1 (color5)")
        self.assertAlmostEqual(float(g._bot_a), 1.0, places=5,
            msg="RED: bot.color.a must be 1 (native .37 not copied)")

        # Test 2: Detachment - mutate returned color, get again
        lua.execute('''
            local ACT = kyohud.hud.actors
            local snap0 = ACT:get_crew_snapshot()
            local human0 = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then human0 = e; break end
            end
            if human0 and human0.color then
                human0.color.r = 999
            end
            local snap1 = ACT:get_crew_snapshot()
            local human1 = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then human1 = e; break end
            end
            _detached_r = human1 and human1.color and human1.color.r
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._detached_r), 0.2, places=5,
            msg="RED: snapshot must be detached (color.r unchanged after mutation)")

        # Test 3: Posthook update - set_teammate_callsign(1, 3) updates human immediately
        lua.execute('''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud

            -- Dispatch real registered posthook
            mgr:set_teammate_callsign(1, 3)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_callsign" then
                    e.fn(mgr, 1, 3)
                end
            end

            local snap2 = ACT:get_crew_snapshot()
            local human2 = nil
            local bot2 = nil
            for _, e in ipairs(snap2) do
                if e.peer_id == 2 then human2 = e end
                if e.ai == true then bot2 = e end
            end

            _human2_r = human2 and human2.color and human2.color.r
            _human2_g = human2 and human2.color and human2.color.g
            _human2_b = human2 and human2.color and human2.color.b

            _bot2_r = bot2 and bot2.color and bot2.color.r
            _bot2_g = bot2 and bot2.color and bot2.color.g
            _bot2_b = bot2 and bot2.color and bot2.color.b
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._human2_r), 0.1, places=5,
            msg="RED: human.color.r must be 0.1 after posthook (color3)")
        self.assertAlmostEqual(float(g._human2_g), 0.9, places=5,
            msg="RED: human.color.g must be 0.9 after posthook (color3)")
        self.assertAlmostEqual(float(g._human2_b), 0.5, places=5,
            msg="RED: human.color.b must be 0.5 after posthook (color3)")

        self.assertAlmostEqual(float(g._bot2_r), 0.8, places=5,
            msg="RED: bot.color.r must remain 0.8 (unchanged)")
        self.assertAlmostEqual(float(g._bot2_g), 0.3, places=5,
            msg="RED: bot.color.g must remain 0.3 (unchanged)")
        self.assertAlmostEqual(float(g._bot2_b), 0.1, places=5,
            msg="RED: bot.color.b must remain 0.1 (unchanged)")

        # Test 4: Out-of-range fallback - id=99 uses last color
        lua.execute('''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud

            mgr:set_teammate_callsign(1, 99)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_callsign" then
                    e.fn(mgr, 1, 99)
                end
            end

            local snap3 = ACT:get_crew_snapshot()
            local human3 = nil
            for _, e in ipairs(snap3) do
                if e.peer_id == 2 then human3 = e; break end
            end

            _human3_r = human3 and human3.color and human3.color.r
            _human3_g = human3 and human3.color and human3.color.g
            _human3_b = human3 and human3.color and human3.color.b
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._human3_r), 0.8, places=5,
            msg="RED: human.color.r must fallback to 0.8 (color5, last entry)")
        self.assertAlmostEqual(float(g._human3_g), 0.3, places=5,
            msg="RED: human.color.g must fallback to 0.3 (color5, last entry)")
        self.assertAlmostEqual(float(g._human3_b), 0.1, places=5,
            msg="RED: human.color.b must fallback to 0.1 (color5, last entry)")


class CrewStaleDeployablePeerReplacementTests(unittest.TestCase):
    """RED: bounded owner transition -- stale deployable crossing peer replacement.

    Setup: human peer2 with equipment registry published (deployable ammo_bag
    amount=2, plain number); refresh0 obtains it. Replace session peer object
    for same id=2 while Criminals record/unit/slot unchanged and PM registry
    table retained identically. refresh .5 must NOT inherit old published
    equipment; new genuine publication in PM registry permits recovery.
    """

    def test_stale_deployable_not_inherited_after_peer_replacement(self):
        """Peer object replaced, same id, PM registry retained: stale deployable cleared.

        Setup: localpeer1 excluded, humanpeer2 slot2 ai=false with unit.
        PM registry _global.synced_deployables[2] = {deployable="ammo_bag", amount=2}
        (plain number). tweak_data.equipments.ammo_bag.text_id="ammo_bag_name".
        refresh_crew(mgr, 0): snapshot[1].equipment.deployable has id="ammo_bag",
        amount=2, name_id="ammo_bag_name".

        Replace session peer object for id=2 (new Peer:new table, same id=2, same
        name/level/rank). Criminals record unchanged (same unit, peer_id=2, panel_id=2).
        PM registry table RETAINED IDENTICALLY (still has synced_deployables[2]).

        refresh_crew(mgr, 0.5): snapshot[1].equipment MUST BE NIL (stale deployable
        NOT inherited across peer replacement).

        Clear PM registry synced_deployables[2] = nil, then republish fresh:
        synced_deployables[2] = {deployable="doctor_bag", amount=1}.
        refresh_crew(mgr, 1): snapshot[1].equipment.deployable must have
        id="doctor_bag", amount=1, name_id="doctor_bag_name" (recovery via new
        genuine publication).
        """
        setup = r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            local unitA = {_alive = true, _label = "unitA", _id = 100}

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = unitA,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })

            local mgr = managers.hud
            mgr._teammate_panels[2] = {
                _peer_id = 2,
                _ai = false,
            }
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            managers.player = managers.player or {}
            managers.player._global = managers.player._global or {}
            managers.player._global.synced_deployables = {
                [2] = {deployable = "ammo_bag", amount = 2}
            }
            managers.player._global.synced_cable_ties = {}
            managers.player._global.synced_grenades = {}

            function managers.player:get_synced_deployable_equipment(peer_id)
                return self._global.synced_deployables[peer_id]
            end
            function managers.player:get_synced_cable_ties(peer_id)
                return self._global.synced_cable_ties[peer_id]
            end
            function managers.player:get_synced_grenades(peer_id)
                return self._global.synced_grenades[peer_id]
            end

            tweak_data = tweak_data or {}
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

            local mgr = managers.hud

            ACT:refresh_crew(mgr, 0)
            local snap0 = ACT:get_crew_snapshot()

            _snap0_len = #snap0
            _human0 = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then _human0 = e; break end
            end
            _human0_eq = _human0 and _human0.equipment or nil
            _human0_deploy = _human0_eq and _human0_eq.deployable or nil
            _human0_deploy_id = _human0_deploy and _human0_deploy.id or nil
            _human0_deploy_amount = _human0_deploy and _human0_deploy.amount or nil
            _human0_deploy_name_id = _human0_deploy and _human0_deploy.name_id or nil

            local Peer = getmetatable(managers.network:session():local_peer())
            local Session = getmetatable(managers.network:session())
            local session = managers.network:session()

            local new_remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session._peers[2] = new_remote_peer

            ACT:refresh_crew(mgr, 0.5)
            local snap1 = ACT:get_crew_snapshot()

            _snap1_len = #snap1
            _human1 = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then _human1 = e; break end
            end
            _human1_eq = _human1 and _human1.equipment or nil
            _human1_deploy = _human1_eq and _human1_eq.deployable or nil

            managers.player._global.synced_deployables[2] = nil

            managers.player._global.synced_deployables[2] = {
                deployable = "doctor_bag",
                amount = 1
            }

            ACT:refresh_crew(mgr, 1)
            local snap2 = ACT:get_crew_snapshot()

            _snap2_len = #snap2
            _human2 = nil
            for _, e in ipairs(snap2) do
                if e.peer_id == 2 then _human2 = e; break end
            end
            _human2_eq = _human2 and _human2.equipment or nil
            _human2_deploy = _human2_eq and _human2_eq.deployable or nil
            _human2_deploy_id = _human2_deploy and _human2_deploy.id or nil
            _human2_deploy_amount = _human2_deploy and _human2_deploy.amount or nil
            _human2_deploy_name_id = _human2_deploy and _human2_deploy.name_id or nil
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._snap0_len), 1.0,
            "RED: pre-replacement snapshot must have 1 entry (remote peer2)")
        self.assertIsNotNone(g._human0,
            "RED: pre-replacement snapshot must include peer2")
        self.assertIsNotNone(g._human0_eq,
            "RED: pre-replacement human.equipment must exist")
        self.assertIsNotNone(g._human0_deploy,
            "RED: pre-replacement human.equipment.deployable must exist")
        self.assertEqual(g._human0_deploy_id, "ammo_bag",
            "RED: pre-replacement deployable.id must be 'ammo_bag'")
        self.assertEqual(float(g._human0_deploy_amount), 2.0,
            "RED: pre-replacement deployable.amount must be 2 (plain number)")
        self.assertEqual(g._human0_deploy_name_id, "ammo_bag_name",
            "RED: pre-replacement deployable.name_id must be 'ammo_bag_name'")

        self.assertEqual(float(g._snap1_len), 1.0,
            "RED: post-replacement snapshot must have 1 entry (peer2 still present)")
        self.assertIsNotNone(g._human1,
            "RED: post-replacement snapshot must include peer2")
        self.assertIs(g._human1_eq, None,
            "RED: post-replacement human.equipment MUST be nil "
            "(stale deployable NOT inherited across peer replacement)")
        self.assertIsNone(g._human1_deploy,
            "RED: post-replacement deployable MUST be nil "
            "(PM registry retained identically but peer object replaced)")

        self.assertEqual(float(g._snap2_len), 1.0,
            "RED: post-recovery snapshot must have 1 entry")
        self.assertIsNotNone(g._human2,
            "RED: post-recovery snapshot must include peer2")
        self.assertIsNotNone(g._human2_eq,
            "RED: post-recovery human.equipment must exist (new genuine publication)")
        self.assertIsNotNone(g._human2_deploy,
            "RED: post-recovery deployable must exist (recovery via fresh publication)")
        self.assertEqual(g._human2_deploy_id, "doctor_bag",
            "RED: post-recovery deployable.id must be 'doctor_bag'")
        self.assertEqual(float(g._human2_deploy_amount), 1.0,
            "RED: post-recovery deployable.amount must be 1")
        self.assertEqual(g._human2_deploy_name_id, "doctor_bag_name",
            "RED: post-recovery deployable.name_id must be 'doctor_bag_name'")


if __name__ == "__main__":
    unittest.main()
