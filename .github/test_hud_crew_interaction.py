"""RED: bounded observed-interaction lifecycle test.

Single test verifying HUDManager:teammate_progress PostHook captures
interaction state per peer and exposes it via get_crew_snapshot() without
refresh. Covers start, time-passes-without-success, cancel, restart+finish,
unknown-peer isolation, and snapshot detachment.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hud_actors import _lua

ROOT = Path(__file__).resolve().parents[1]


class CrewInteractionLifecycleTests(unittest.TestCase):

    def test_interaction_lifecycle(self):
        setup = r'''
            _game_t = 0

            local game_timer = newproxy(true)
            local gt_mt = debug.getmetatable(game_timer)
            gt_mt.__index = {}
            function gt_mt.__index:time() return _game_t end

            TimerManager = newproxy(true)
            local tm_mt = debug.getmetatable(TimerManager)
            tm_mt.__index = {}
            function tm_mt.__index:game() return game_timer end

            _timer_type = type(TimerManager)

            _teammate_progress_calls = 0
            function HUDManager:teammate_progress(peer_id, type_index, enabled, tweak_data_id, timer, success)
                _teammate_progress_calls = _teammate_progress_calls + 1
            end

            local Peer = {}
            Peer.__index = Peer
            function Peer:new(id, name, level, rank, unit)
                return setmetatable({_id=id,_name=name,_level=level,_rank=rank,_unit=unit}, self)
            end
            function Peer:id() return self._id end
            function Peer:name() return self._name end
            function Peer:level() return self._level end
            function Peer:rank() return self._rank end
            function Peer:unit() return self._unit end

            local Session = {}
            Session.__index = Session
            function Session:new(local_peer)
                return setmetatable({_local_peer=local_peer,_peers={}}, self)
            end
            function Session:local_peer() return self._local_peer end
            function Session:peer(id) return self._peers[id] end
            function Session:_register_peer(p) self._peers[p:id()] = p end

            local local_peer = Peer:new(1, "LocalHost", 0, 0, nil)
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            local remote_peer = Peer:new(2, "RemotePeer", 5, 0, nil)
            session:_register_peer(remote_peer)
            managers.network = managers.network or {}
            managers.network._session = session
            function managers.network:session() return self._session end

            local CriminalsManager = {}
            CriminalsManager.__index = CriminalsManager
            function CriminalsManager:new()
                return setmetatable({_characters={}}, self)
            end
            function CriminalsManager:characters() return self._characters end
            function CriminalsManager:_set_character(idx, rec)
                self._characters[idx] = rec
            end
            function CriminalsManager:character_data_by_peer_id(peer_id)
                for _, rec in ipairs(self._characters) do
                    if rec.peer_id == peer_id then return rec.data end
                end
                return nil
            end
            managers.criminals = managers.criminals or CriminalsManager:new()

            managers.criminals:_set_character(1, {
                name="american", taken=true, unit=nil, peer_id=1,
                data={ai=false, panel_id=4},
            })
            managers.criminals:_set_character(2, {
                name="spanish", taken=true, unit=nil, peer_id=2,
                data={ai=false, panel_id=2},
            })

            local mgr = managers.hud
            mgr._teammate_panels = {}
            mgr._teammate_panels[2] = {_peer_id=2, _ai=false}
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken=true}
            end

            local Loc = {}
            Loc.__index = Loc
            function Loc:text(key) return key end
            managers.localization = managers.localization
                or setmetatable({}, Loc)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(r'''
            local ACT = kyohud.hud.actors
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"; return
            end
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"; return
            end
            _api_missing = false

            local mgr = managers.hud

            _hook_registered = false
            for _, e in ipairs(Hooks._all) do
                if e.method == "teammate_progress" then
                    _hook_registered = true; break
                end
            end

            ACT:refresh_crew(mgr, 0)
            local snap0 = ACT:get_crew_snapshot()
            _snap0_count = #snap0
            _snap0_p2_int = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then
                    _snap0_p2_int = e.interaction; break
                end
            end

            _game_t = 1
            mgr:teammate_progress(2, 1, true, "lockpick", 10, nil)
            for _, e in ipairs(Hooks._all) do
                if e.method == "teammate_progress" then
                    e.fn(mgr, 2, 1, true, "lockpick", 10, nil)
                end
            end

            local snap1 = ACT:get_crew_snapshot()
            _s1_int = nil; _s1_pid = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then
                    _s1_int = e.interaction; _s1_pid = e.peer_id; break
                end
            end
            _s1_type=nil;_s1_tweak=nil;_s1_en=nil;_s1_dur=nil
            _s1_started=nil;_s1_succ=nil
            if _s1_int then
                _s1_type=_s1_int.type_index
                _s1_tweak=_s1_int.tweak_data_id
                _s1_en=_s1_int.enabled
                _s1_dur=_s1_int.duration
                _s1_started=_s1_int.started_t
                _s1_succ=_s1_int.success
            end

            _game_t = 100
            local snap100 = ACT:get_crew_snapshot()
            _s100_int = nil
            for _, e in ipairs(snap100) do
                if e.peer_id == 2 then
                    _s100_int = e.interaction; break
                end
            end
            _s100_succ=nil;_s100_started=nil;_s100_dur=nil
            if _s100_int then
                _s100_succ=_s100_int.success
                _s100_started=_s100_int.started_t
                _s100_dur=_s100_int.duration
            end

            _game_t = 101
            mgr:teammate_progress(2, 1, false, "lockpick", 0, false)
            for _, e in ipairs(Hooks._all) do
                if e.method == "teammate_progress" then
                    e.fn(mgr, 2, 1, false, "lockpick", 0, false)
                end
            end
            local snapC = ACT:get_crew_snapshot()
            _sc_int = nil
            for _, e in ipairs(snapC) do
                if e.peer_id == 2 then
                    _sc_int = e.interaction; break
                end
            end
            _sc_en=nil;_sc_succ=nil
            if _sc_int then
                _sc_en=_sc_int.enabled
                _sc_succ=_sc_int.success
            end

            _game_t = 101
            mgr:teammate_progress(2, 2, true, "ammo_bag", 5, nil)
            for _, e in ipairs(Hooks._all) do
                if e.method == "teammate_progress" then
                    e.fn(mgr, 2, 2, true, "ammo_bag", 5, nil)
                end
            end

            _game_t = 103
            mgr:teammate_progress(2, 2, false, "ammo_bag", 0, true)
            for _, e in ipairs(Hooks._all) do
                if e.method == "teammate_progress" then
                    e.fn(mgr, 2, 2, false, "ammo_bag", 0, true)
                end
            end
            local snapF = ACT:get_crew_snapshot()
            _sf_int=nil;_sf_pid=nil
            for _, e in ipairs(snapF) do
                if e.peer_id == 2 then
                    _sf_int=e.interaction;_sf_pid=e.peer_id;break
                end
            end
            _sf_succ=nil;_sf_en=nil;_sf_type=nil;_sf_tweak=nil
            if _sf_int then
                _sf_succ=_sf_int.success
                _sf_en=_sf_int.enabled
                _sf_type=_sf_int.type_index
                _sf_tweak=_sf_int.tweak_data_id
            end

            _calls_before = _teammate_progress_calls
            mgr:teammate_progress(99, 1, true, "lockpick", 10, nil)
            for _, e in ipairs(Hooks._all) do
                if e.method == "teammate_progress" then
                    e.fn(mgr, 99, 1, true, "lockpick", 10, nil)
                end
            end
            _calls_after = _teammate_progress_calls

            local snapP = ACT:get_crew_snapshot()
            _p_count=#snapP;_p_has99=false;_p_p2succ=nil
            for _, e in ipairs(snapP) do
                if e.peer_id==99 then _p_has99=true end
                if e.peer_id==2 and e.interaction then
                    _p_p2succ=e.interaction.success
                end
            end

            local snapM = ACT:get_crew_snapshot()
            _dur_before=nil
            for _, e in ipairs(snapM) do
                if e.peer_id==2 and e.interaction then
                    _dur_before=e.interaction.duration
                    e.interaction.duration=99999;break
                end
            end
            local snapA = ACT:get_crew_snapshot()
            _dur_after=nil
            for _, e in ipairs(snapA) do
                if e.peer_id==2 and e.interaction then
                    _dur_after=e.interaction.duration;break
                end
            end
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(g._timer_type, "userdata",
            "RED: TimerManager must be userdata (native singleton rejection)")

        self.assertTrue(g._hook_registered,
            "RED: PostHook on teammate_progress must be registered by actors.lua")

        self.assertEqual(int(g._snap0_count), 1,
            "RED: initial crew must have exactly 1 non-local occupant")
        self.assertIsNone(g._snap0_p2_int,
            "RED: initial snapshot peer2 interaction must be nil")

        self.assertIsNotNone(g._s1_int,
            "RED: after start event, interaction must be present")
        self.assertEqual(float(g._s1_type), 1.0,
            "RED: type_index must be 1")
        self.assertEqual(g._s1_tweak, "lockpick",
            "RED: tweak_data_id must be 'lockpick'")
        self.assertIs(g._s1_en, True,
            "RED: enabled must be True after start")
        self.assertEqual(float(g._s1_dur), 10.0,
            "RED: duration must be 10")
        self.assertEqual(float(g._s1_started), 1.0,
            "RED: started_t must be 1 (game time at dispatch)")
        self.assertIsNone(g._s1_succ,
            "RED: success must be nil after start")
        self.assertEqual(float(g._s1_pid), 2.0,
            "RED: interaction must be bound to peer_id 2")

        self.assertIsNone(g._s100_succ,
            "RED: success must remain nil at game_t=100 (expiry NOT success)")
        self.assertEqual(float(g._s100_started), 1.0,
            "RED: started_t must remain 1 at game_t=100")
        self.assertEqual(float(g._s100_dur), 10.0,
            "RED: duration must remain 10 at game_t=100")

        self.assertIs(g._sc_en, False,
            "RED: cancel must set enabled to False exact")
        self.assertIs(g._sc_succ, False,
            "RED: cancel must set success to False exact (not and/or idiom)")

        self.assertIs(g._sf_succ, True,
            "RED: finish must set success to True")
        self.assertIs(g._sf_en, False,
            "RED: finish must set enabled to False")
        self.assertEqual(float(g._sf_type), 2.0,
            "RED: finish type_index must be 2")
        self.assertEqual(g._sf_tweak, "ammo_bag",
            "RED: finish tweak_data_id must be 'ammo_bag'")
        self.assertEqual(float(g._sf_pid), 2.0,
            "RED: finish interaction must be bound to peer_id 2")

        self.assertEqual(float(g._calls_after), float(g._calls_before) + 1.0,
            "RED: native teammate_progress must be called for peer99")
        self.assertFalse(bool(g._p_has99),
            "RED: peer99 must not appear in crew roster (no fabricated entry)")
        self.assertEqual(int(g._p_count), 1,
            "RED: crew count must remain 1 after peer99 event")
        self.assertIs(g._p_p2succ, True,
            "RED: peer2 interaction must be unchanged after peer99 event")

        self.assertIsNotNone(g._dur_before,
            "RED: pre-mutation duration must be present")
        self.assertEqual(float(g._dur_before), float(g._dur_after),
            "RED: mutating exported interaction must not affect getter (detached)")
