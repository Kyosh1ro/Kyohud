"""LOT5 crew roster slice -- actors:get_crew_snapshot() RED vertical tracer.

Scope: single test verifying get_crew_snapshot() returns a detached Lua array
of up to 3 non-local occupants with correct identity fields. Excludes local
peer, includes remote human without unit and two distinct bots. Human
level/rank from peer (rank 0 preserved); bot level/rank nil.

RED state: actors:get_crew_snapshot() and crew-aware actors:refresh(manager)
do not exist yet. Tests must fail with explicit messages.
"""
from pathlib import Path
import sys
import unittest

from lupa.luajit21 import LuaRuntime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hud_actors import STUBS, NATIVE_HEALTH_ARMOR_FIXTURE

ROOT = Path(__file__).resolve().parents[1]
ACTORS_PATH = ROOT / "lua" / "hud" / "actors.lua"

NATIVE_CRIMINALS_FIXTURE = r'''
-- Native-shaped criminals manager fixture.
-- criminals:characters() returns an array of records {name, taken, unit, peer_id, data={ai, panel_id}}.
-- This is the authoritative identity source for crew roster.
local CriminalsManager = {}
CriminalsManager.__index = CriminalsManager

function CriminalsManager:new()
    return setmetatable({_characters = {}}, self)
end

function CriminalsManager:characters()
    return self._characters
end

function CriminalsManager:_set_character(idx, rec)
    self._characters[idx] = rec
end

managers.criminals = managers.criminals or CriminalsManager:new()
'''

NATIVE_SESSION_FIXTURE = r'''
-- Native-shaped session/peer fixture.
-- Session :local_peer()/:peer(id); Peer :id()/:name()/:level()/:rank()/:unit().
local Peer = {}
Peer.__index = Peer

function Peer:new(id, name, level, rank, unit)
    return setmetatable({
        _id = id,
        _name = name,
        _level = level,
        _rank = rank,
        _unit = unit,
    }, self)
end

function Peer:id() return self._id end
function Peer:name() return self._name end
function Peer:level() return self._level end
function Peer:rank() return self._rank end
function Peer:unit() return self._unit end

local Session = {}
Session.__index = Session

function Session:new(local_peer)
    return setmetatable({_local_peer = local_peer, _peers = {}}, self)
end

function Session:local_peer()
    return self._local_peer
end

function Session:peer(id)
    return self._peers[id]
end

function Session:_register_peer(p)
    self._peers[p:id()] = p
end

managers.network = managers.network or {}
managers.network._session = managers.network._session or Session:new(Peer:new(1, "LocalHost", 0, 0, nil))
function managers.network:session()
    return self._session
end
'''

NATIVE_LOCALIZATION_FIXTURE = r'''
-- Native-shaped localization fixture for bot names.
-- managers.localization:text("menu_" .. character_name) returns display name.
local LocalizationManager = {}
LocalizationManager.__index = LocalizationManager

local _bot_names = {
    russian = "Dallas",
    german = "Hoxton",
    spanish = "Chains",
    american = "Wolf",
}

function LocalizationManager:text(key)
    if type(key) ~= "string" then return key end
    local stripped = key:match("^menu_(.+)$")
    if stripped and _bot_names[stripped] then
        return _bot_names[stripped]
    end
    return key
end

managers.localization = managers.localization or setmetatable({}, LocalizationManager)
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua(setup=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute("HUDManager.PLAYER_PANEL = 4")
    lua.execute(NATIVE_CRIMINALS_FIXTURE)
    lua.execute(NATIVE_SESSION_FIXTURE)
    lua.execute(NATIVE_LOCALIZATION_FIXTURE)
    if setup:
        lua.execute(setup)
    actors_src = _read(ACTORS_PATH)
    actors_exists = actors_src is not None
    if actors_src:
        lua.execute(actors_src)
    return lua, actors_exists


class ActorsCrewRosterTests(unittest.TestCase):
    """RED: get_crew_snapshot() returns detached array of non-local occupants.

    Excludes actual local peer even outside slot 4; includes remote human
    without unit, two bots with peer=nil but distinct character names/tokens.
    Human level/rank from peer; rank 0 valid. Bots: name from
    managers.localization:text("menu_"..name), level/rank nil.
    """

    def test_roster_excludes_local_includes_human_and_bots(self):
        """Fresh roster: 3 non-local occupants, local peer excluded.

        Setup: local peer id=1 (NOT in slot 4). Criminals array has 4 taken
        characters: slot 1 = local (peer_id=1), slot 2 = remote human
        (peer_id=2, no unit, level=5, rank=0), slot 3 = bot (name="russian",
        peer_id=nil, ai=true), slot 4 = bot (name="german", peer_id=nil,
        ai=true). get_crew_snapshot() must return exactly 3 entries, none
        matching local peer_id=1. Human entry: peer_id=2, name="AlPhA",
        level=5, rank=0, ai=false, unit_id absent. Bot entries: ai=true,
        peer_id=nil, level=nil, rank=nil, names from localization, distinct
        tokens.
        """
        setup = '''
            -- Local peer: id=1, level=10, rank=2, no unit
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            -- Remote human peer: id=2, level=5, rank=0, no unit
            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            -- Criminals: 4 characters, all taken
            -- idx 1 = local peer (peer_id=1) -> must be EXCLUDED
            -- idx 2 = remote human (peer_id=2, ai=false, unit=nil)
            -- idx 3 = bot russian (peer_id=nil, ai=true)
            -- idx 4 = bot german (peer_id=nil, ai=true)
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
                unit = nil,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })
            managers.criminals:_set_character(3, {
                name = "russian",
                taken = true,
                unit = nil,
                peer_id = nil,
                data = {ai = true, panel_id = 3},
            })
            managers.criminals:_set_character(4, {
                name = "german",
                taken = true,
                unit = nil,
                peer_id = nil,
                data = {ai = true, panel_id = 4},
            })

            -- Native HUD manager fixture
            local mgr = managers.hud
            mgr._teammate_panels = {}
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"
                return
            end
            _api_missing = false

            local mgr = managers.hud
            ACT:refresh_crew(mgr, 0)
            local snap = ACT:get_crew_snapshot()
            _snap_type = type(snap)
            _snap_len = snap and #snap or -1

            -- Extract entries by position
            _entries = {}
            if snap then
                for i = 1, #snap do
                    _entries[i] = snap[i]
                end
            end

            -- Check no local peer (peer_id=1) in snapshot
            _has_local = false
            for i, e in ipairs(_entries) do
                if e.peer_id == 1 then
                    _has_local = true
                    break
                end
            end

            -- Find human entry (peer_id=2)
            _human = nil
            for i, e in ipairs(_entries) do
                if e.peer_id == 2 then
                    _human = e
                    break
                end
            end

            -- Find bot entries (ai=true, peer_id=nil)
            _bots = {}
            for i, e in ipairs(_entries) do
                if e.ai == true and e.peer_id == nil then
                    table.insert(_bots, e)
                end
            end
            _bot_count = #_bots
        ''')
        g = lua.globals()

        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(g._snap_type, "table",
            "RED: get_crew_snapshot must return a table")
        self.assertEqual(g._snap_len, 3,
            "RED: snapshot must contain exactly 3 non-local occupants")
        self.assertFalse(bool(g._has_local),
            "RED: snapshot must exclude local peer (peer_id=1)")

        self.assertIsNotNone(g._human,
            "RED: snapshot must include remote human (peer_id=2)")

        lua.execute('''
            local h = _human
            _h_peer_id = h and h.peer_id or nil
            _h_ai = h.ai
            _h_name = h and h.name or nil
            _h_level = h and h.level
            _h_rank = h and h.rank
            _h_char = h and h.character_name or nil
            _h_pos = h and h.position or nil
            _h_slot = h and h.slot or nil
            _h_token = h and h.occupant_token or nil
            _h_unit = h and h.unit_id
        ''')
        g = lua.globals()
        self.assertEqual(float(g._h_peer_id), 2.0,
            "RED: human peer_id must be 2")
        self.assertIs(g._h_ai, False,
            "RED: human ai must be false")
        self.assertEqual(g._h_name, "AlPhA",
            "RED: human name must come from peer:name()")
        self.assertEqual(float(g._h_level), 5.0,
            "RED: human level must come from peer:level()")
        self.assertEqual(float(g._h_rank), 0.0,
            "RED: human rank 0 must be preserved (valid value)")
        self.assertIsNone(g._h_unit,
            "RED: human without unit must have unit_id nil")
        self.assertEqual(g._h_char, "spanish",
            "RED: human character_name must be 'spanish'")
        self.assertEqual(float(g._h_slot), 2.0,
            "RED: human slot must be 2")
        self.assertEqual(float(g._h_pos), 1.0,
            "RED: human position must be 1")
        self.assertIsNotNone(g._h_token,
            "RED: human must have occupant_token")

        self.assertEqual(float(g._bot_count), 2.0,
            "RED: snapshot must include 2 bots")

        lua.execute('''
            _bot_names = {}
            _bot_chars = {}
            _bot_tokens = {}
            _bot_levels = {}
            _bot_ranks = {}
            _bot_peer_ids = {}
            _bot_positions = {}
            for i, b in ipairs(_bots) do
                _bot_names[i] = b.name
                _bot_chars[i] = b.character_name
                _bot_tokens[i] = b.occupant_token
                _bot_levels[i] = b.level
                _bot_ranks[i] = b.rank
                _bot_peer_ids[i] = b.peer_id
                _bot_positions[i] = b.position
            end
        ''')
        g = lua.globals()

        _expected_bots = [
            {"char": "russian", "name": "Dallas", "pos": 2},
            {"char": "german", "name": "Hoxton", "pos": 3},
        ]
        for i, exp in enumerate(_expected_bots, 1):
            name = g._bot_names[i]
            char = g._bot_chars[i]
            token = g._bot_tokens[i]
            level = g._bot_levels[i]
            rank = g._bot_ranks[i]
            peer_id = g._bot_peer_ids[i]
            pos = g._bot_positions[i]

            self.assertIsNotNone(name,
                f"RED: bot {i} must have name from localization")
            self.assertEqual(name, exp["name"],
                f"RED: bot {i} name must be '{exp['name']}'")
            self.assertEqual(char, exp["char"],
                f"RED: bot {i} character_name must be '{exp['char']}'")
            self.assertIsNotNone(token,
                f"RED: bot {i} must have occupant_token")
            self.assertIsNone(level,
                f"RED: bot {i} level must be nil (no peer)")
            self.assertIsNone(rank,
                f"RED: bot {i} rank must be nil (no peer)")
            self.assertIsNone(peer_id,
                f"RED: bot {i} peer_id must be nil")
            self.assertEqual(float(pos), float(exp["pos"]),
                f"RED: bot {i} position must be {exp['pos']}")

        self.assertNotEqual(g._bot_tokens[1], g._bot_tokens[2],
            "RED: bots must have distinct occupant_tokens")
        self.assertNotEqual(g._bot_chars[1], g._bot_chars[2],
            "RED: bots must have distinct character_names")


    def test_slot_uses_panel_id_not_array_index(self):
        """Slot must come from source record data.panel_id, not criminals array index.

        Setup: criminals array index 1 = remote peer (panel_id=3), index 2 = local
        peer (panel_id=4). After refresh, snapshot[1].slot must be 3.
        """
        setup = '''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "Remote", 5, 0, nil)
            session:_register_peer(remote_peer)

            managers.criminals:_set_character(1, {
                name = "russian",
                taken = true,
                unit = nil,
                peer_id = 2,
                data = {ai = false, panel_id = 3},
            })
            managers.criminals:_set_character(2, {
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
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"
                return
            end
            _api_missing = false
            ACT:refresh_crew(managers.hud, 0)
            local snap = ACT:get_crew_snapshot()
            _first_slot = snap and snap[1] and snap[1].slot
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return
        self.assertEqual(float(g._first_slot), 3.0,
            "RED: snapshot[1].slot must be source data.panel_id=3, not array index 1")


    def test_initial_order_by_panel_id_and_sticky_positions(self):
        """Order by data.panel_id initially; positions sticky per occupant_token.

        Array index 1 = human peer2 panel_id=3, index 2 = bot russian panel_id=1.
        After refresh: snap ordered by panel_id: bot(pos=1,slot=1), human(pos=2,slot=3).
        Move human to panel_id=2, bot to panel_id=3, refresh: each keeps same
        occupant_token and position, but slots update to new panel_ids.
        """
        setup = '''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            managers.criminals:_set_character(1, {
                name = "spanish",
                taken = true,
                unit = nil,
                peer_id = 2,
                data = {ai = false, panel_id = 3},
            })
            managers.criminals:_set_character(2, {
                name = "russian",
                taken = true,
                unit = nil,
                peer_id = nil,
                data = {ai = true, panel_id = 1},
            })
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
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"
                return
            end
            _api_missing = false

            ACT:refresh_crew(managers.hud, 0)
            local snap = ACT:get_crew_snapshot()

            _init_count = 0
            _init_pos1 = nil
            _init_pos2 = nil
            for _, e in pairs(snap) do
                _init_count = _init_count + 1
                if e.position == 1 then _init_pos1 = e end
                if e.position == 2 then _init_pos2 = e end
            end

            _pos1_is_bot = _init_pos1 and (_init_pos1.ai == true) and (_init_pos1.peer_id == nil)
            _pos1_slot = _init_pos1 and _init_pos1.slot
            _pos1_char = _init_pos1 and _init_pos1.character_name
            _pos2_is_human = _init_pos2 and (_init_pos2.ai == false) and (_init_pos2.peer_id == 2)
            _pos2_slot = _init_pos2 and _init_pos2.slot
            _pos2_char = _init_pos2 and _init_pos2.character_name

            _bot_token_init = _init_pos1 and _init_pos1.occupant_token
            _human_token_init = _init_pos2 and _init_pos2.occupant_token

            local chars = managers.criminals:characters()
            chars[1].data.panel_id = 2
            chars[2].data.panel_id = 3

            ACT:refresh_crew(managers.hud, 0.5)
            local snap2 = ACT:get_crew_snapshot()

            _human_after = nil
            _bot_after = nil
            for _, e in pairs(snap2) do
                if e.peer_id == 2 then _human_after = e end
                if e.ai == true and e.peer_id == nil then _bot_after = e end
            end

            _human_token_same = _human_after and (_human_after.occupant_token == _human_token_init)
            _bot_token_same = _bot_after and (_bot_after.occupant_token == _bot_token_init)
            _human_pos_sticky = _human_after and (_human_after.position == 2)
            _bot_pos_sticky = _bot_after and (_bot_after.position == 1)
            _human_slot_updated = _human_after and (_human_after.slot == 2)
            _bot_slot_updated = _bot_after and (_bot_after.slot == 3)
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._init_count), 2.0,
            "RED: must have 2 non-local occupants")
        self.assertIs(g._pos1_is_bot, True,
            "RED: position 1 must be bot (panel_id=1 sorts first)")
        self.assertEqual(g._pos1_char, "russian",
            "RED: position 1 character must be russian")
        self.assertEqual(float(g._pos1_slot), 1.0,
            "RED: bot initial slot must be panel_id 1")
        self.assertIs(g._pos2_is_human, True,
            "RED: position 2 must be human peer2 (panel_id=3)")
        self.assertEqual(g._pos2_char, "spanish",
            "RED: position 2 character must be spanish")
        self.assertEqual(float(g._pos2_slot), 3.0,
            "RED: human initial slot must be panel_id 3")

        self.assertIs(g._human_token_same, True,
            "RED: human occupant_token must be unchanged after panel move")
        self.assertIs(g._bot_token_same, True,
            "RED: bot occupant_token must be unchanged after panel move")
        self.assertIs(g._human_pos_sticky, True,
            "RED: human position must remain 2 after panel move")
        self.assertIs(g._bot_pos_sticky, True,
            "RED: bot position must remain 1 after panel move")
        self.assertIs(g._human_slot_updated, True,
            "RED: human slot must update to 2 (new panel_id)")
        self.assertIs(g._bot_slot_updated, True,
            "RED: bot slot must update to 3 (new panel_id)")


    def test_bot_token_lifecycle_and_snapshot_detachment(self):
        """Bot departure frees position; return gets NEW token + first free slot.

        Two bots russian(panel_id=1)/german(panel_id=2). Refresh captures tokens
        and positions. Set russian taken=false, refresh: german retains position 2.
        Set russian taken=true, refresh: russian gets NEW token(!=former) and
        first free position 1. Mutate old snapshot then getter without refresh
        verifies deep copy detachment.
        """
        setup = '''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            managers.criminals:_set_character(1, {
                name = "russian",
                taken = true,
                unit = nil,
                peer_id = 0,
                data = {ai = true, panel_id = 1},
            })
            managers.criminals:_set_character(2, {
                name = "german",
                taken = true,
                unit = nil,
                peer_id = 0,
                data = {ai = true, panel_id = 2},
            })
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
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"
                return
            end
            _api_missing = false

            ACT:refresh_crew(managers.hud, 0)
            local snap1 = ACT:get_crew_snapshot()

            _initial_count = 0
            _russian_token_old = nil
            _russian_pos_old = nil
            _russian_peer_id_old = nil
            _german_token_old = nil
            _german_pos_old = nil
            _german_peer_id_old = nil
            for _, e in pairs(snap1) do
                _initial_count = _initial_count + 1
                if e.character_name == "russian" then
                    _russian_token_old = e.occupant_token
                    _russian_pos_old = e.position
                    _russian_peer_id_old = e.peer_id
                end
                if e.character_name == "german" then
                    _german_token_old = e.occupant_token
                    _german_pos_old = e.position
                    _german_peer_id_old = e.peer_id
                end
            end

            managers.criminals:characters()[1].taken = false
            ACT:refresh_crew(managers.hud, 0.5)
            local snap2 = ACT:get_crew_snapshot()

            _after_remove_count = 0
            _german_pos_after_remove = nil
            _german_token_after_remove = nil
            _german_peer_id_after = nil
            for _, e in pairs(snap2) do
                _after_remove_count = _after_remove_count + 1
                if e.character_name == "german" then
                    _german_pos_after_remove = e.position
                    _german_token_after_remove = e.occupant_token
                    _german_peer_id_after = e.peer_id
                end
            end

            _dense_count = #snap2
            _dense_first_is_german = snap2[1] ~= nil and snap2[1].character_name == "german"

            _german_retained_pos = (_german_pos_after_remove == _german_pos_old)
            _german_retained_token = (_german_token_after_remove == _german_token_old)

            managers.criminals:characters()[1].taken = true
            ACT:refresh_crew(managers.hud, 1.0)
            local snap3 = ACT:get_crew_snapshot()

            _after_return_count = 0
            _russian_token_new = nil
            _russian_pos_new = nil
            _russian_peer_id_new = nil
            for _, e in pairs(snap3) do
                _after_return_count = _after_return_count + 1
                if e.character_name == "russian" then
                    _russian_token_new = e.occupant_token
                    _russian_pos_new = e.position
                    _russian_peer_id_new = e.peer_id
                end
            end

            _russian_token_changed = (_russian_token_new ~= _russian_token_old)
            _russian_got_first_free = (_russian_pos_new == 1)

            local snap_check = ACT:get_crew_snapshot()
            _snap_check_1_name_orig = snap_check[1] and snap_check[1].name
            _snap_check_1_pos_orig = snap_check[1] and snap_check[1].position
            if snap_check[1] then
                snap_check[1].name = "MUTATED_NAME"
                snap_check[1].position = 999
            end

            local snap_check2 = ACT:get_crew_snapshot()
            _detached = true
            _snap_check2_len = #snap_check2
            _snap_check2_1_name = snap_check2[1] and snap_check2[1].name
            _snap_check2_1_pos = snap_check2[1] and snap_check2[1].position
            for _, e in pairs(snap_check2) do
                if e.name == "MUTATED_NAME" then _detached = false end
                if e.position == 999 then _detached = false end
            end
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertIsNotNone(g._russian_token_old,
            "RED: must capture russian initial token")
        self.assertIsNotNone(g._german_token_old,
            "RED: must capture german initial token")
        self.assertEqual(float(g._initial_count), 2.0,
            "RED: initial must have 2 bots")

        self.assertEqual(float(g._after_remove_count), 1.0,
            "RED: after russian removed, exactly 1 bot remains")
        self.assertIs(g._german_retained_pos, True,
            "RED: german must retain position 2 after russian removed")
        self.assertIs(g._german_retained_token, True,
            "RED: german must retain same occupant_token after russian removed")

        self.assertEqual(float(g._after_return_count), 2.0,
            "RED: after russian returns, 2 bots again")
        self.assertIs(g._russian_token_changed, True,
            "RED: returning russian must get NEW token, never former token")
        self.assertIs(g._russian_got_first_free, True,
            "RED: returning russian must get first free position 1")

        self.assertIs(g._detached, True,
            "RED: get_crew_snapshot must return detached deep copy")
        self.assertEqual(g._snap_check2_1_name, g._snap_check_1_name_orig,
            "RED: second snapshot first entry name must equal saved original after first snapshot mutated")
        self.assertEqual(float(g._snap_check2_1_pos), float(g._snap_check_1_pos_orig),
            "RED: second snapshot first entry position must equal saved original after first snapshot mutated")
        self.assertEqual(float(g._snap_check2_len), 2.0,
            "RED: second snapshot count must remain 2 after first snapshot mutated")

        self.assertEqual(float(g._dense_count), 1.0,
            "RED: snap2 must be dense array with exactly 1 entry (german only, no hole at position 1)")
        self.assertIs(g._dense_first_is_german, True,
            "RED: snap2[1] must be german — exported array must be dense even when presentation position has hole")
        self.assertIsNone(g._russian_peer_id_old,
            "RED: snapshot bot peer_id must be nil even when source criminals record uses sentinel peer_id=0")
        self.assertIsNone(g._german_peer_id_old,
            "RED: snapshot bot peer_id must be nil even when source criminals record uses sentinel peer_id=0")
        self.assertIsNone(g._german_peer_id_after,
            "RED: snapshot bot peer_id must remain nil after russian removal")
        self.assertIsNone(g._russian_peer_id_new,
            "RED: returning bot peer_id must be nil in snapshot")


    def test_session_replace_and_heist_start_reset_tokens(self):
        """Session replacement forces new token; on_heist_start prevents collision.

        Human peer2 refresh captures token. Replace session with new Session
        object and new peer2 object at same ID=2. Refresh: token must differ.
        on_heist_start then refresh: token must not collide ANY prior token.
        """
        setup = '''
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
            mgr._teammate_panels = {}
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"
                return
            end
            if not ACT.on_heist_start then
                _api_missing = "on_heist_start"
                return
            end
            _api_missing = false

            ACT:refresh_crew(managers.hud, 0)
            local snap1 = ACT:get_crew_snapshot()

            _initial_count = 0
            _token_old = nil
            for _, e in pairs(snap1) do
                _initial_count = _initial_count + 1
                if e.peer_id == 2 then
                    _token_old = e.occupant_token
                end
            end

            local Peer = getmetatable(managers.network:session():local_peer())
            local new_local = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local new_session = Session:new(new_local)
            new_session:_register_peer(new_local)
            local new_remote = Peer:new(2, "AlPhA", 5, 0, nil)
            new_session:_register_peer(new_remote)
            managers.network._session = new_session

            ACT:refresh_crew(managers.hud, 0.5)
            local snap2 = ACT:get_crew_snapshot()

            _after_replace_count = 0
            _token_after_replace = nil
            for _, e in pairs(snap2) do
                _after_replace_count = _after_replace_count + 1
                if e.peer_id == 2 then
                    _token_after_replace = e.occupant_token
                end
            end
            _token_differs = (_token_after_replace ~= _token_old)

            ACT:on_heist_start(managers.hud)
            ACT:refresh_crew(managers.hud, 1.0)
            local snap3 = ACT:get_crew_snapshot()

            _after_heist_count = 0
            _token_after_heist = nil
            for _, e in pairs(snap3) do
                _after_heist_count = _after_heist_count + 1
                if e.peer_id == 2 then
                    _token_after_heist = e.occupant_token
                end
            end

            _no_collision = true
            if _token_after_heist == _token_old then _no_collision = false end
            if _token_after_heist == _token_after_replace then _no_collision = false end
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertIsNotNone(g._token_old,
            "RED: must capture initial human peer2 token")
        self.assertEqual(float(g._initial_count), 1.0,
            "RED: initial must have exactly 1 non-local occupant")

        self.assertIsNotNone(g._token_after_replace,
            "RED: must capture token after session replacement")
        self.assertIs(g._token_differs, True,
            "RED: session replacement must produce different token for same peer ID")

        self.assertIsNotNone(g._token_after_heist,
            "RED: must capture token after on_heist_start + refresh")
        self.assertIs(g._no_collision, True,
            "RED: on_heist_start must prevent token collision with all prior tokens")


    def test_refresh_crew_api_contract_and_throttling(self):
        """ACT:refresh_crew(manager, t) is explicit crew collection API with throttling.

        Verify:
        - criminals:characters call count instrumentation
        - repeated ACT:refresh never scans roster (criminals:characters call count stays 0)
        - ACT:refresh_crew(manager, 0) collects (criminals:characters called once)
        - repeated refresh_crew at .1, .49 do not rescan (call count stays 1)
        - at .5 rescans and sees changed bot name/record (call count becomes 2, sees new name)
        - snapshot getter does not scan (call count stays 2)
        """
        setup = '''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "russian",
                taken = true,
                unit = nil,
                peer_id = 0,
                data = {ai = true, panel_id = 1},
            })

            local mgr = managers.hud
            mgr._teammate_panels = {}
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            local criminals = managers.criminals
            _G._characters_calls = 0
            local _original_characters = criminals.characters
            function criminals:characters()
                _G._characters_calls = _G._characters_calls + 1
                return _original_characters(self)
            end
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            if not ACT.refresh then
                _api_missing = "refresh"
                return
            end
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"
                return
            end
            _api_missing = false

            local calls_initial = _G._characters_calls
            ACT:refresh(managers.hud)
            local calls_after_refresh1 = _G._characters_calls
            ACT:refresh(managers.hud)
            local calls_after_refresh2 = _G._characters_calls
            ACT:refresh(managers.hud)
            local calls_after_refresh3 = _G._characters_calls

            ACT:refresh_crew(managers.hud, 0)
            local calls_after_refresh_crew_0 = _G._characters_calls

            ACT:refresh_crew(managers.hud, 0.1)
            local calls_after_refresh_crew_01 = _G._characters_calls
            ACT:refresh_crew(managers.hud, 0.49)
            local calls_after_refresh_crew_049 = _G._characters_calls

            managers.criminals._characters[2].name = "german"
            ACT:refresh_crew(managers.hud, 0.5)
            local calls_after_refresh_crew_05 = _G._characters_calls
            local snap = ACT:get_crew_snapshot()
            _bot_name_after_05 = nil
            for _, e in pairs(snap) do
                if e.ai == true and e.peer_id == nil then
                    _bot_name_after_05 = e.character_name
                    break
                end
            end

            ACT:get_crew_snapshot()
            ACT:get_crew_snapshot()
            local calls_after_snapshot = _G._characters_calls

            _calls_initial = calls_initial
            _calls_after_refresh1 = calls_after_refresh1
            _calls_after_refresh2 = calls_after_refresh2
            _calls_after_refresh3 = calls_after_refresh3
            _calls_after_refresh_crew_0 = calls_after_refresh_crew_0
            _calls_after_refresh_crew_01 = calls_after_refresh_crew_01
            _calls_after_refresh_crew_049 = calls_after_refresh_crew_049
            _calls_after_refresh_crew_05 = calls_after_refresh_crew_05
            _calls_after_snapshot = calls_after_snapshot
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._calls_initial), 0.0,
            "RED: initial characters call count must be 0")
        self.assertEqual(float(g._calls_after_refresh1), 0.0,
            "RED: ACT:refresh must not call criminals:characters")
        self.assertEqual(float(g._calls_after_refresh2), 0.0,
            "RED: repeated ACT:refresh must not call criminals:characters")
        self.assertEqual(float(g._calls_after_refresh3), 0.0,
            "RED: repeated ACT:refresh must not call criminals:characters")

        self.assertEqual(float(g._calls_after_refresh_crew_0), 1.0,
            "RED: ACT:refresh_crew(manager, 0) must call criminals:characters once")

        self.assertEqual(float(g._calls_after_refresh_crew_01), 1.0,
            "RED: ACT:refresh_crew at t=0.1 must not rescan (< 0.5s)")
        self.assertEqual(float(g._calls_after_refresh_crew_049), 1.0,
            "RED: ACT:refresh_crew at t=0.49 must not rescan (< 0.5s)")

        self.assertEqual(float(g._calls_after_refresh_crew_05), 2.0,
            "RED: ACT:refresh_crew at t=0.5 must rescan (>= 0.5s)")
        self.assertEqual(g._bot_name_after_05, "german",
            "RED: after rescan at t=0.5, bot character_name must be updated to 'german'")

        self.assertEqual(float(g._calls_after_snapshot), 2.0,
            "RED: get_crew_snapshot must not call criminals:characters")


    def test_source_replacement_same_peer_clears_slot_metrics(self):
        """Replacing criminals source with same-shaped instance clears slot metrics.

        Setup: remote peer2 at slot 2, panel _peer_id=2, _ai=false, matching
        criminals record panel_id=2. refresh_crew(mgr,0), seed health 25/100
        via native fixture + dispatch real registered health posthook. Assert
        get_actor(2).health ratio .25 and crew entry/token positive.

        Replace managers.criminals with a native-shaped NEW instance containing
        same record / SAME peer object in SAME session and SAME HUD manager.
        refresh_crew at .5. Expect crew identity still peer2 with NEW occupant
        token (source invalidated). get_actor(2) must be absent or health
        absent (old observation must not survive source replacement).

        Publish new health 60/100 via posthook and assert recovery ratio .6.
        No test-side production/cache injection.
        """
        setup = NATIVE_HEALTH_ARMOR_FIXTURE + r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            managers.criminals:_set_character(1, {
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
            if not ACT.get_actor then
                _api_missing = "get_actor"
                return
            end
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            _api_missing = false

            local mgr = managers.hud

            ACT:refresh_crew(mgr, 0)

            local hp1 = {current = 25, total = 100}
            mgr:set_teammate_health(2, hp1)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp1)
                end
            end

            local actor_before = ACT:get_actor(2)
            _actor_before_exists = actor_before ~= nil
            _ratio_before = actor_before and actor_before.health
                and actor_before.health.ratio or nil
            _valid_before = actor_before and actor_before.health
                and actor_before.health.valid or nil

            local snap_before = ACT:get_crew_snapshot()
            _crew_count_before = #snap_before
            _token_before = nil
            for _, e in ipairs(snap_before) do
                if e.peer_id == 2 then
                    _token_before = e.occupant_token
                    break
                end
            end
            _token_positive_before = type(_token_before) == "number"
                and _token_before > 0

            local NewCriminalsManager = {}
            NewCriminalsManager.__index = NewCriminalsManager
            function NewCriminalsManager:new()
                return setmetatable({_characters = {}}, self)
            end
            function NewCriminalsManager:characters()
                return self._characters
            end
            function NewCriminalsManager:_set_character(idx, rec)
                self._characters[idx] = rec
            end

            local new_criminals = NewCriminalsManager:new()
            new_criminals:_set_character(1, {
                name = "spanish",
                taken = true,
                unit = nil,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })
            managers.criminals = new_criminals

            ACT:refresh_crew(mgr, 0.5)

            local snap_after = ACT:get_crew_snapshot()
            _crew_count_after = #snap_after
            _token_after = nil
            _peer_id_after = nil
            for _, e in ipairs(snap_after) do
                if e.peer_id == 2 then
                    _token_after = e.occupant_token
                    _peer_id_after = e.peer_id
                    break
                end
            end
            _token_positive_after = type(_token_after) == "number"
                and _token_after > 0
            _token_changed = (_token_after ~= _token_before)

            local actor_after = ACT:get_actor(2)
            _actor_after_exists = actor_after ~= nil
            _health_after = actor_after and actor_after.health or nil
            _health_absent = (not _actor_after_exists)
                or (not _health_after)

            local hp2 = {current = 60, total = 100}
            mgr:set_teammate_health(2, hp2)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp2)
                end
            end

            local actor_recovered = ACT:get_actor(2)
            _ratio_recovered = actor_recovered and actor_recovered.health
                and actor_recovered.health.ratio or nil
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertTrue(g._actor_before_exists,
            "RED: get_actor(2) must exist after seeding health via posthook")
        self.assertAlmostEqual(float(g._ratio_before), 0.25, places=5,
            msg="RED: health ratio must be 0.25 (25/100) before source replacement")
        self.assertTrue(g._valid_before,
            "RED: health must be valid before source replacement")
        self.assertEqual(float(g._crew_count_before), 1.0,
            "RED: crew snapshot must have 1 entry before replacement")
        self.assertTrue(g._token_positive_before,
            "RED: crew occupant_token must be positive before replacement")

        self.assertEqual(float(g._crew_count_after), 1.0,
            "RED: crew snapshot must still have 1 entry after source replacement")
        self.assertEqual(float(g._peer_id_after), 2.0,
            "RED: crew entry must still be peer2 after source replacement")
        self.assertTrue(g._token_positive_after,
            "RED: crew occupant_token must be positive after source replacement")
        self.assertTrue(g._token_changed,
            "RED: crew occupant_token must be NEW after source replacement (old token invalidated)")
        self.assertTrue(g._health_absent,
            "RED: get_actor(2) must be absent or health absent after source replacement (old observation must not survive)")

        self.assertIsNotNone(g._ratio_recovered,
            "RED: health ratio must be present after new health callback post-replacement")
        self.assertAlmostEqual(float(g._ratio_recovered), 0.6, places=5,
            msg="RED: health ratio must recover to 0.6 (60/100) after new callback")



    def test_peer_object_replacement_same_id_clears_health_observation(self):
        """Replacing session peer object at same id=2 clears old health observation.

        Setup: remote peer2 (name="AlPhA", level=5, rank=0) in session._peers[2],
        criminals record peer_id=2 panel_id=2, HUD panel _peer_id=2/_ai=false.
        refresh_crew(mgr,0), then dispatch registered health 25/100. Assert
        get_actor(2) health ratio .25 and valid.

        Replace session._peers[2] with new Peer:new(2,"Replacement",42,1,nil),
        leave criminals record and HUD panel peer_id unchanged. refresh_crew at .5.
        Snapshot must show name="Replacement", level=42, rank=1, new token.
        get_actor(2) must be absent or health absent (old observation must not
        survive peer object replacement).

        Dispatch fresh health 60/100 and assert recovery ratio .6.
        No test-side production/cache injection.
        """
        setup = NATIVE_HEALTH_ARMOR_FIXTURE + r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            managers.criminals:_set_character(1, {
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
            if not ACT.get_actor then
                _api_missing = "get_actor"
                return
            end
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            _api_missing = false

            local mgr = managers.hud

            ACT:refresh_crew(mgr, 0)

            local hp1 = {current = 25, total = 100}
            mgr:set_teammate_health(2, hp1)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp1)
                end
            end

            local actor_before = ACT:get_actor(2)
            _actor_before_exists = actor_before ~= nil
            _ratio_before = actor_before and actor_before.health
                and actor_before.health.ratio or nil
            _valid_before = actor_before and actor_before.health
                and actor_before.health.valid or nil

            local snap_before = ACT:get_crew_snapshot()
            _crew_count_before = #snap_before
            _token_before = nil
            _name_before = nil
            _level_before = nil
            _rank_before = nil
            for _, e in ipairs(snap_before) do
                if e.peer_id == 2 then
                    _token_before = e.occupant_token
                    _name_before = e.name
                    _level_before = e.level
                    _rank_before = e.rank
                    break
                end
            end
            _token_positive_before = type(_token_before) == "number"
                and _token_before > 0

            local session = managers.network:session()
            local Peer = getmetatable(session:local_peer())
            local new_peer = Peer:new(2, "Replacement", 42, 1, nil)
            session._peers[2] = new_peer

            ACT:refresh_crew(mgr, 0.5)

            local snap_after = ACT:get_crew_snapshot()
            _crew_count_after = #snap_after
            _token_after = nil
            _name_after = nil
            _level_after = nil
            _rank_after = nil
            _peer_id_after = nil
            for _, e in ipairs(snap_after) do
                if e.peer_id == 2 then
                    _token_after = e.occupant_token
                    _name_after = e.name
                    _level_after = e.level
                    _rank_after = e.rank
                    _peer_id_after = e.peer_id
                    break
                end
            end
            _token_positive_after = type(_token_after) == "number"
                and _token_after > 0
            _token_changed = (_token_after ~= _token_before)

            local actor_after = ACT:get_actor(2)
            _actor_after_exists = actor_after ~= nil
            _health_after = actor_after and actor_after.health or nil
            _health_absent = (not _actor_after_exists)
                or (not _health_after)

            local hp2 = {current = 60, total = 100}
            mgr:set_teammate_health(2, hp2)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp2)
                end
            end

            local actor_recovered = ACT:get_actor(2)
            _ratio_recovered = actor_recovered and actor_recovered.health
                and actor_recovered.health.ratio or nil
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertTrue(g._actor_before_exists,
            "RED: get_actor(2) must exist after seeding health via posthook")
        self.assertAlmostEqual(float(g._ratio_before), 0.25, places=5,
            msg="RED: health ratio must be 0.25 (25/100) before peer replacement")
        self.assertTrue(g._valid_before,
            "RED: health must be valid before peer replacement")
        self.assertEqual(float(g._crew_count_before), 1.0,
            "RED: crew snapshot must have 1 entry before replacement")
        self.assertTrue(g._token_positive_before,
            "RED: crew occupant_token must be positive before replacement")
        self.assertEqual(g._name_before, "AlPhA",
            "RED: name must be 'AlPhA' before peer replacement")
        self.assertEqual(float(g._level_before), 5.0,
            "RED: level must be 5 before peer replacement")
        self.assertEqual(float(g._rank_before), 0.0,
            "RED: rank must be 0 before peer replacement")

        self.assertEqual(float(g._crew_count_after), 1.0,
            "RED: crew snapshot must still have 1 entry after peer replacement")
        self.assertEqual(float(g._peer_id_after), 2.0,
            "RED: crew entry must still be peer_id=2 after peer replacement")
        self.assertEqual(g._name_after, "Replacement",
            "RED: name must be 'Replacement' after peer replacement")
        self.assertEqual(float(g._level_after), 42.0,
            "RED: level must be 42 after peer replacement")
        self.assertEqual(float(g._rank_after), 1.0,
            "RED: rank must be 1 after peer replacement")
        self.assertTrue(g._token_positive_after,
            "RED: crew occupant_token must be positive after peer replacement")
        self.assertTrue(g._token_changed,
            "RED: crew occupant_token must be NEW after peer replacement")
        self.assertTrue(g._health_absent,
            "RED: get_actor(2) must be absent or health absent after peer replacement (old observation must not survive)")

        self.assertIsNotNone(g._ratio_recovered,
            "RED: health ratio must be present after new health callback post-replacement")
        self.assertAlmostEqual(float(g._ratio_recovered), 0.6, places=5,
            msg="RED: health ratio must recover to 0.6 (60/100) after new callback")


    def test_remote_unit_replacement_same_peer_clears_metrics(self):
        """Replacing unit table at same peer/slot preserves token/position but clears metrics.

        Setup: remote peer2 in session, HUD slot 2, criminals record unit=unitA
        (native-shaped alive table), peer._unit=unitA. refresh_crew(mgr,0), seed
        health 25/100 via native fixture + dispatch registered posthook. Assert
        get_actor(2) health ratio .25, positive unit_id, positive token, position.

        Change SAME criminals record.unit to distinct alive table unitB AND
        peer._unit to unitB. refresh_crew at .5 must keep occupant_token and
        position, change unit_id, clear prior get_actor(2).health.

        Fresh health 60/100 callback recovers ratio .6.
        No test-side production/cache injection.
        """
        setup = NATIVE_HEALTH_ARMOR_FIXTURE + r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            local unitA = {_alive = true, _label = "unitA"}
            local unitB = {_alive = true, _label = "unitB"}
            _G._unitA = unitA
            _G._unitB = unitB

            managers.criminals:_set_character(1, {
                name = "spanish",
                taken = true,
                unit = unitA,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })
            remote_peer._unit = unitA

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
            if not ACT.get_actor then
                _api_missing = "get_actor"
                return
            end
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            _api_missing = false

            local mgr = managers.hud

            ACT:refresh_crew(mgr, 0)

            local hp1 = {current = 25, total = 100}
            mgr:set_teammate_health(2, hp1)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp1)
                end
            end

            local actor_before = ACT:get_actor(2)
            _actor_before_exists = actor_before ~= nil
            _ratio_before = actor_before and actor_before.health
                and actor_before.health.ratio or nil
            _valid_before = actor_before and actor_before.health
                and actor_before.health.valid or nil

            local snap_before = ACT:get_crew_snapshot()
            _crew_count_before = #snap_before
            _token_before = nil
            _position_before = nil
            _unit_id_crew_before = nil
            for _, e in ipairs(snap_before) do
                if e.peer_id == 2 then
                    _token_before = e.occupant_token
                    _position_before = e.position
                    _unit_id_crew_before = e.unit_id
                    break
                end
            end
            _token_positive_before = type(_token_before) == "number"
                and _token_before > 0
            _unit_id_positive_before = type(_unit_id_crew_before) == "number"
                and _unit_id_crew_before > 0

            local rec = managers.criminals:characters()[1]
            rec.unit = _G._unitB
            local session = managers.network:session()
            local peer = session:peer(2)
            peer._unit = _G._unitB

            ACT:refresh_crew(mgr, 0.5)

            local snap_after = ACT:get_crew_snapshot()
            _crew_count_after = #snap_after
            _token_after = nil
            _position_after = nil
            _unit_id_crew_after = nil
            _peer_id_after = nil
            for _, e in ipairs(snap_after) do
                if e.peer_id == 2 then
                    _token_after = e.occupant_token
                    _position_after = e.position
                    _unit_id_crew_after = e.unit_id
                    _peer_id_after = e.peer_id
                    break
                end
            end
            _token_same = (_token_after == _token_before)
            _position_same = (_position_after == _position_before)
            _unit_id_changed = (_unit_id_crew_after ~= _unit_id_crew_before)

            local actor_after = ACT:get_actor(2)
            _actor_after_exists = actor_after ~= nil
            _health_after = actor_after and actor_after.health or nil
            _health_absent = (not _actor_after_exists)
                or (not _health_after)

            local hp2 = {current = 60, total = 100}
            mgr:set_teammate_health(2, hp2)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp2)
                end
            end

            local actor_recovered = ACT:get_actor(2)
            _ratio_recovered = actor_recovered and actor_recovered.health
                and actor_recovered.health.ratio or nil
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertTrue(g._actor_before_exists,
            "RED: get_actor(2) must exist after seeding health via posthook")
        self.assertAlmostEqual(float(g._ratio_before), 0.25, places=5,
            msg="RED: health ratio must be 0.25 (25/100) before unit replacement")
        self.assertTrue(g._valid_before,
            "RED: health must be valid before unit replacement")
        self.assertEqual(float(g._crew_count_before), 1.0,
            "RED: crew snapshot must have 1 entry before unit replacement")
        self.assertTrue(g._token_positive_before,
            "RED: crew occupant_token must be positive before unit replacement")
        self.assertTrue(g._unit_id_positive_before,
            "RED: crew unit_id must be positive before unit replacement")
        self.assertIsNotNone(g._position_before,
            "RED: crew position must be present before unit replacement")

        self.assertEqual(float(g._crew_count_after), 1.0,
            "RED: crew snapshot must still have 1 entry after unit replacement")
        self.assertEqual(float(g._peer_id_after), 2.0,
            "RED: crew entry must still be peer_id=2 after unit replacement")
        self.assertIs(g._token_same, True,
            "RED: occupant_token must be preserved after unit replacement (same peer)")
        self.assertIs(g._position_same, True,
            "RED: position must be preserved after unit replacement")
        self.assertIs(g._unit_id_changed, True,
            "RED: unit_id must change after unit replacement (different unit table)")
        self.assertTrue(g._health_absent,
            "RED: get_actor(2) must be absent or health absent after unit replacement (old observation must not survive)")

        self.assertIsNotNone(g._ratio_recovered,
            "RED: health ratio must be present after new health callback post-unit-replacement")
        self.assertAlmostEqual(float(g._ratio_recovered), 0.6, places=5,
            msg="RED: health ratio must recover to 0.6 (60/100) after new callback")


    def test_local_peer_nil_interrupt_clears_roster_health_probe(self):
        """Nil local_peer interrupts roster; health observation does not survive.

        Setup: remote peer2 "Remote" in session, criminals record peer_id=2
        panel_id=2 ai=false, HUD mgr panel2 _peer_id=2/_ai=false.
        refresh_crew(mgr,0), dispatch registered health 25/100 via native
        fixture. Assert get_actor(2) health ratio .25. Capture initial token.

        Set session._local_peer=nil (interrupt local peer reference).
        refresh_crew(mgr,0.5). Expect get_crew_snapshot() empty (#==0) AND
        get_actor(2) nil or health absent (old observation must not survive
        nil-local-peer interruption — SOL in-memory probe: roster==0 but
        health .25 remains must be rejected).

        Restore same session._local_peer reference. refresh_crew(mgr,1).
        Expect peer2 returns with NEW occupant_token (proof was interrupted).
        Health remains unknown until new callback. Dispatch health 60/100 via
        posthook and assert ratio .6. No test-side production/cache injection.
        """
        setup = NATIVE_HEALTH_ARMOR_FIXTURE + r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "Remote", 5, 0, nil)
            session:_register_peer(remote_peer)

            managers.criminals:_set_character(1, {
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
            if not ACT.get_actor then
                _api_missing = "get_actor"
                return
            end
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            _api_missing = false

            local mgr = managers.hud

            ACT:refresh_crew(mgr, 0)

            local hp1 = {current = 25, total = 100}
            mgr:set_teammate_health(2, hp1)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp1)
                end
            end

            local actor_before = ACT:get_actor(2)
            _actor_before_exists = actor_before ~= nil
            _ratio_before = actor_before and actor_before.health
                and actor_before.health.ratio or nil

            local snap_before = ACT:get_crew_snapshot()
            _crew_count_before = #snap_before
            _token_before = nil
            for _, e in ipairs(snap_before) do
                if e.peer_id == 2 then
                    _token_before = e.occupant_token
                    break
                end
            end
            _token_positive_before = type(_token_before) == "number"
                and _token_before > 0

            local session = managers.network:session()
            _saved_local_peer = session._local_peer
            session._local_peer = nil

            ACT:refresh_crew(mgr, 0.5)

            local snap_interrupted = ACT:get_crew_snapshot()
            _crew_count_interrupted = #snap_interrupted

            local actor_interrupted = ACT:get_actor(2)
            _actor_interrupted_exists = actor_interrupted ~= nil
            _health_interrupted = actor_interrupted and actor_interrupted.health or nil
            _health_absent_interrupted = (not _actor_interrupted_exists)
                or (not _health_interrupted)

            session._local_peer = _saved_local_peer

            ACT:refresh_crew(mgr, 1.0)

            local snap_restored = ACT:get_crew_snapshot()
            _crew_count_restored = #snap_restored
            _token_restored = nil
            _peer_id_restored = nil
            for _, e in ipairs(snap_restored) do
                if e.peer_id == 2 then
                    _token_restored = e.occupant_token
                    _peer_id_restored = e.peer_id
                    break
                end
            end
            _token_positive_restored = type(_token_restored) == "number"
                and _token_restored > 0
            _token_changed = (_token_restored ~= _token_before)

            local actor_restored = ACT:get_actor(2)
            _actor_restored_exists = actor_restored ~= nil
            _health_restored = actor_restored and actor_restored.health or nil
            _health_absent_restored = (not _actor_restored_exists)
                or (not _health_restored)

            local hp2 = {current = 60, total = 100}
            mgr:set_teammate_health(2, hp2)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp2)
                end
            end

            local actor_recovered = ACT:get_actor(2)
            _ratio_recovered = actor_recovered and actor_recovered.health
                and actor_recovered.health.ratio or nil
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertTrue(g._actor_before_exists,
            "RED: get_actor(2) must exist after seeding health via posthook")
        self.assertAlmostEqual(float(g._ratio_before), 0.25, places=5,
            msg="RED: health ratio must be 0.25 (25/100) before interruption")
        self.assertEqual(float(g._crew_count_before), 1.0,
            "RED: crew snapshot must have 1 entry before interruption")
        self.assertTrue(g._token_positive_before,
            "RED: crew occupant_token must be positive before interruption")

        self.assertEqual(float(g._crew_count_interrupted), 0.0,
            "RED: crew snapshot must be empty (#==0) after local_peer=nil interruption")
        self.assertTrue(g._health_absent_interrupted,
            "RED: get_actor(2) must be absent or health absent after local_peer=nil interruption (SOL probe: roster==0 but health .25 must not survive)")

        self.assertEqual(float(g._crew_count_restored), 1.0,
            "RED: crew snapshot must have 1 entry after restoring local_peer")
        self.assertEqual(float(g._peer_id_restored), 2.0,
            "RED: crew entry must be peer_id=2 after restoring local_peer")
        self.assertTrue(g._token_positive_restored,
            "RED: crew occupant_token must be positive after restoring local_peer")
        self.assertTrue(g._token_changed,
            "RED: crew occupant_token must be NEW after restoring local_peer (proof was interrupted)")
        self.assertTrue(g._health_absent_restored,
            "RED: health must remain unknown until new callback after restoring local_peer")

        self.assertIsNotNone(g._ratio_recovered,
            "RED: health ratio must be present after new health callback post-restore")
        self.assertAlmostEqual(float(g._ratio_recovered), 0.6, places=5,
            msg="RED: health ratio must recover to 0.6 (60/100) after new callback")


    def test_reentrant_remove_add_transaction_clears_stale_health(self):
        """Reentrant remove_teammate_panel→add_teammate_panel must not publish stale health.

        Setup: remote peer2 at slot 2, panel _peer_id=2, _ai=false, matching
        criminals record panel_id=2. Before actors load, define native-shaped
        HUDManager.add_teammate_panel(character_name,player_name,ai,peer_id) that
        sets panel2 peer2, dispatches native set_teammate_health(2,{25,100}), then
        returns 2. Define HUDManager.remove_teammate_panel(id) that recursively
        calls add_teammate_panel (simulating roster shift).

        Define _call_hud(method,...) dispatcher: run every matching pre hook,
        original HUDManager method on managers.hud, then post hooks; preserve
        arguments and return.

        refresh_crew(mgr,0), then _call_hud("remove_teammate_panel",2). Expect
        get_actor(2) absent or health absent immediately after outer remove/add
        (publication during transaction ambiguous).

        Then _call_hud("set_teammate_health",2,{current=60,total=100}) AFTER
        outer remove returns must recover ratio .6. Assert inner native health
        publication actually ran once and hooks health actually exist; no skip,
        no production methods/cache injection.

        Expected RED: stale .25 (registered pre/post transaction protection missing).
        """
        setup = NATIVE_HEALTH_ARMOR_FIXTURE + r'''
            -- Native-shaped add/remove teammate panel with reentrant dispatch
            local _inner_health_published = 0
            local _dispatched_health_calls = 0

            function HUDManager:add_teammate_panel(character_name, player_name, ai, peer_id)
                -- Set panel2 peer2
                if not self._teammate_panels[2] then
                    self._teammate_panels[2] = {}
                end
                self._teammate_panels[2]._peer_id = peer_id or 2
                self._teammate_panels[2]._ai = ai or false

                -- Dispatch native health 25/100 internally
                local hp = {current = 25, total = 100}
                _call_hud("set_teammate_health", 2, hp)
                _inner_health_published = _inner_health_published + 1

                return 2
            end

            function HUDManager:remove_teammate_panel(id)
                -- Recursively call add_teammate_panel (simulating roster shift)
                _call_hud("add_teammate_panel", "spanish", "AlPhA", false, 2)
            end

            function HUDManager:_inner_health_count()
                return _inner_health_published
            end

            -- _call_hud dispatcher: pre hooks, original method, post hooks
            function _call_hud(method, ...)
                local args = {...}
                for _, e in ipairs(Hooks._all) do
                    if e.kind == "pre" and e.method == method then
                        e.fn(managers.hud, unpack(args))
                    end
                end
                local result = HUDManager[method](managers.hud, unpack(args))
                for _, e in ipairs(Hooks._all) do
                    if e.kind == "post" and e.method == method then
                        e.fn(managers.hud, unpack(args))
                    end
                end
                if method == "set_teammate_health" then
                    _dispatched_health_calls = _dispatched_health_calls + 1
                end
                return result
            end

            function HUDManager:_dispatched_health_count()
                return _dispatched_health_calls
            end

            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            managers.criminals:_set_character(1, {
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
            if not ACT.get_actor then
                _api_missing = "get_actor"
                return
            end
            _api_missing = false

            local mgr = managers.hud

            -- Initial roster load
            ACT:refresh_crew(mgr, 0)

            -- Dispatch registered health posthook to seed .25
            local hp1 = {current = 25, total = 100}
            mgr:set_teammate_health(2, hp1)
            for _, e in ipairs(Hooks._all) do
                if e.kind == "post" and e.method == "set_teammate_health" then
                    e.fn(mgr, 2, hp1)
                end
            end

            local actor_before = ACT:get_actor(2)
            _actor_before_exists = actor_before ~= nil
            _ratio_before = actor_before and actor_before.health
                and actor_before.health.ratio or nil

            -- Verify inner native health publication ran via add_teammate_panel
            _inner_count_before = mgr:_inner_health_count()
            _dispatched_health_before = mgr:_dispatched_health_count()

            -- Execute reentrant remove_teammate_panel (which calls add_teammate_panel)
            _call_hud("remove_teammate_panel", 2)

            -- Immediately after outer remove/add: expect ambiguous publication
            local actor_during = ACT:get_actor(2)
            _actor_during_exists = actor_during ~= nil
            _health_during = actor_during and actor_during.health or nil
            _health_absent_during = (not _actor_during_exists)
                or (not _health_during)

            -- Verify inner native health publication actually ran once
            _inner_count_after = mgr:_inner_health_count()
            _inner_published_once = (_inner_count_after == _inner_count_before + 1)

            -- Verify dispatched health callback was exercised via dispatcher
            _dispatched_health_after = mgr:_dispatched_health_count()
            _dispatched_health_incremented = (_dispatched_health_after >= _dispatched_health_before + 1)

            -- Verify hooks health actually exist (set_teammate_health hooks registered)
            _hooks_health_exist = false
            for _, e in ipairs(Hooks._all) do
                if e.kind == "post" and e.method == "set_teammate_health" then
                    _hooks_health_exist = true
                    break
                end
            end

            -- After outer remove returns, publish new health 60/100
            local hp2 = {current = 60, total = 100}
            _call_hud("set_teammate_health", 2, hp2)

            local actor_recovered = ACT:get_actor(2)
            _ratio_recovered = actor_recovered and actor_recovered.health
                and actor_recovered.health.ratio or nil
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertTrue(g._actor_before_exists,
            "RED: get_actor(2) must exist after seeding health via posthook")
        self.assertAlmostEqual(float(g._ratio_before), 0.25, places=5,
            msg="RED: health ratio must be 0.25 (25/100) before reentrant remove")

        self.assertTrue(g._health_absent_during,
            "RED: get_actor(2) must be absent or health absent immediately after outer remove/add (publication during transaction ambiguous)")

        self.assertTrue(g._inner_published_once,
            "RED: inner native health publication must have run exactly once during add_teammate_panel")
        self.assertTrue(g._dispatched_health_incremented,
            "RED: dispatcher health callback counter must have incremented during reentrant transaction (proves inner dispatch exercised)")
        self.assertTrue(g._hooks_health_exist,
            "RED: set_teammate_health post hooks must be registered")

        self.assertIsNotNone(g._ratio_recovered,
            "RED: health ratio must be present after new health callback post-transaction")
        self.assertAlmostEqual(float(g._ratio_recovered), 0.6, places=5,
            msg="RED: health ratio must recover to 0.6 (60/100) after new callback")


    def test_local_panel_numeric_peer_id_preserves_health_during_add_transaction(self):
        """Local panel with numeric peer_id must preserve health during add_teammate_panel.

        Setup: panel4 _peer_id=1, _ai=false. session.local_peer:id()==1.
        managers.player:player_unit() returns alive local unit. Native
        HUDManager:add_teammate_panel(character_name,player_name,ai,peer_id)
        dispatches set_teammate_health(4,{70,100}) via _call_hud dispatcher.

        Invoke real registered add pre, then native add, then post via one
        dispatcher. Expect get_actor(4).health valid ratio .7 because genuine
        local update MUST survive unrelated roster transaction (SOL review:
        _is_panel_local returns false for numeric peer_id, but local peer also
        has numeric id).

        Assert native method health callback executed. Assert existing
        health/armor/revives/condition/remove pre hook IDs remain EXACT
        KyohHUD_Actors_Health, KyohHUD_Actors_Armor, KyohHUD_Actors_Revives,
        KyohHUD_Actors_Condition, KyohHUD_Actors_RemovePanel (production
        accidentally renamed KyohUD..., causing reload double registration).
        """
        setup = NATIVE_HEALTH_ARMOR_FIXTURE + r'''
            -- Native no-op methods for revives/condition/remove
            function HUDManager:set_teammate_revives(i, amount) end
            function HUDManager:set_teammate_condition(i, icon, text) end
            function HUDManager:remove_teammate_panel(id) end

            -- Native-shaped add_teammate_panel that dispatches health on slot4
            local _native_health_invoked = 0

            function HUDManager:add_teammate_panel(character_name, player_name, ai, peer_id)
                -- Set panel4 peer1 (local)
                if not self._teammate_panels[4] then
                    self._teammate_panels[4] = {}
                end
                self._teammate_panels[4]._peer_id = peer_id or 1
                self._teammate_panels[4]._ai = ai or false

                -- Dispatch native health 70/100 on slot4
                local hp = {current = 70, total = 100}
                _call_hud("set_teammate_health", 4, hp)
                _native_health_invoked = _native_health_invoked + 1

                return 4
            end

            function HUDManager:_native_health_count()
                return _native_health_invoked
            end

            -- _call_hud dispatcher: pre hooks, original method, post hooks
            function _call_hud(method, ...)
                local args = {...}
                for _, e in ipairs(Hooks._all) do
                    if e.kind == "pre" and e.method == method then
                        e.fn(managers.hud, unpack(args))
                    end
                end
                local result = HUDManager[method](managers.hud, unpack(args))
                for _, e in ipairs(Hooks._all) do
                    if e.kind == "post" and e.method == method then
                        e.fn(managers.hud, unpack(args))
                    end
                end
                return result
            end

            -- Session/peer setup: local peer id=1
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            -- Local player unit (alive)
            local local_unit = {_alive = true, _label = "local_unit"}
            managers.player = managers.player or {}
            function managers.player:player_unit()
                return local_unit
            end

            -- Criminals: slot 4 = local peer (peer_id=1)
            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = local_unit,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })

            local mgr = managers.hud
            mgr._teammate_panels[4] = {
                _peer_id = 1,
                _ai = false,
            }
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end
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
            if not ACT.get_actor then
                _api_missing = "get_actor"
                return
            end
            _api_missing = false

            local mgr = managers.hud

            -- Initial roster load
            ACT:refresh_crew(mgr, 0)

            -- Verify native health count before
            _native_health_before = mgr:_native_health_count()

            -- Invoke add_teammate_panel via dispatcher (which dispatches health)
            _call_hud("add_teammate_panel", "american", "LocalHost", false, 1)

            -- Verify native health callback actually executed
            _native_health_after = mgr:_native_health_count()
            _native_health_executed = (_native_health_after == _native_health_before + 1)

            -- Expect get_actor(4).health valid ratio .7
            local actor = ACT:get_actor(4)
            _actor_exists = actor ~= nil
            _health_exists = actor and actor.health or nil
            _ratio = actor and actor.health and actor.health.ratio or nil
            _valid = actor and actor.health and actor.health.valid or nil

            -- Assert hook IDs are EXACT (production accidentally renamed KyohUD...)
            _hook_ids = {}
            for _, e in ipairs(Hooks._all) do
                if e.id then
                    _hook_ids[e.id] = true
                end
            end

            _has_health_id = _hook_ids["KyohHUD_Actors_Health"] == true
            _has_armor_id = _hook_ids["KyohHUD_Actors_Armor"] == true
            _has_revives_id = _hook_ids["KyohHUD_Actors_Revives"] == true
            _has_condition_id = _hook_ids["KyohHUD_Actors_Condition"] == true
            _has_remove_id = _hook_ids["KyohHUD_Actors_RemovePanel"] == true

            -- Also check for wrong IDs (KyohUD with uppercase UD)
            _has_wrong_health_id = _hook_ids["KyohUD_Actors_Health"] == true
            _has_wrong_armor_id = _hook_ids["KyohUD_Actors_Armor"] == true
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertTrue(g._actor_exists,
            "RED: get_actor(4) must exist after add_teammate_panel dispatched health")
        self.assertTrue(g._health_exists,
            "RED: get_actor(4).health must exist (genuine local update must survive roster transaction)")
        self.assertTrue(g._valid,
            "RED: get_actor(4).health must be valid")
        self.assertAlmostEqual(float(g._ratio), 0.7, places=5,
            msg="RED: get_actor(4).health ratio must be 0.7 (70/100) — local panel with numeric peer_id must preserve health")

        self.assertTrue(g._native_health_executed,
            "RED: native add_teammate_panel must have invoked set_teammate_health exactly once")

        self.assertTrue(g._has_health_id,
            "RED: hook ID must be exactly 'KyohHUD_Actors_Health' (not 'KyohUD_Actors_Health' — production accidentally renamed)")
        self.assertTrue(g._has_armor_id,
            "RED: hook ID must be exactly 'KyohHUD_Actors_Armor' (not 'KyohUD_Actors_Armor')")
        self.assertTrue(g._has_revives_id,
            "RED: hook ID must be exactly 'KyohHUD_Actors_Revives' (not 'KyohUD_Actors_Revives')")
        self.assertTrue(g._has_condition_id,
            "RED: hook ID must be exactly 'KyohHUD_Actors_Condition' (not 'KyohUD_Actors_Condition')")
        self.assertTrue(g._has_remove_id,
            "RED: hook ID must be exactly 'KyohHUD_Actors_RemovePanel' (not 'KyohUD_Actors_RemovePanel')")

        self.assertFalse(g._has_wrong_health_id,
            "RED: must NOT have wrong ID 'KyohUD_Actors_Health' (should be 'KyohHUD_Actors_Health')")
        self.assertFalse(g._has_wrong_armor_id,
            "RED: must NOT have wrong ID 'KyohUD_Actors_Armor' (should be 'KyohHUD_Actors_Armor')")


if __name__ == "__main__":
    unittest.main()
