"""LOT1 -- hud/native_visibility.lua: targeted reversible visibility control."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
NV_PATH = ROOT / "lua" / "hud" / "native_visibility.lua"

ACCEPTANCE_VISIBILITY_ENV = '''
function alive(x) return x~=nil and x.live~=false end
function obj()
 return {live=true,v=true,a=.37, visible=function(s) return s.v end,
  set_visible=function(s,v) s.v=v end, alpha=function(s) return s.a end,
  set_alpha=function(s,v) s.a=v end}
end
'''

STUBS = '''
kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end
kyohud.hud = kyohud.hud or {}
function log(...) end
function alive(x) return x ~= nil and x._alive ~= false end
'''

DIESEL_OBJ = '''
function _make_obj(name)
    return {
        _alive = true, _name = name,
        _vis = true, _alpha = 1,
        visible = function(self) return self._vis end,
        set_visible = function(self, v) self._vis = v end,
        alpha = function(self) return self._alpha end,
        set_alpha = function(self, a) self._alpha = a end,
    }
end
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua_with(wl_lua):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(DIESEL_OBJ)
    src = _read(NV_PATH)
    if src:
        lua.execute(src)
    if wl_lua:
        lua.execute(wl_lua)
    return lua, src is not None


def acceptance_env():
    l = LuaRuntime(unpack_returned_tuples=True)
    l.execute(STUBS)
    l.execute(ACCEPTANCE_VISIBILITY_ENV)
    l.execute(_read(NV_PATH))
    return l


def _svc_with_obj(obj_name="hud_assault"):
    lua, _ = _lua_with(f'''
        _obj = _make_obj("{obj_name}")
        _wl = {{ [_obj] = {{visible = true, alpha = true}} }}
        svc = kyohud.hud.native_visibility:new(_wl)
    ''')
    return lua


class NVExistsTests(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(NV_PATH.is_file())

    def test_namespace(self):
        lua, ok = _lua_with(None)
        self.assertTrue(ok)
        lua.execute("assert(type(kyohud.hud.native_visibility) == 'table')")

    def test_constructor_exists(self):
        lua, _ = _lua_with(None)
        lua.execute("assert(type(kyohud.hud.native_visibility.new) == 'function')")


class NVProductionTests(unittest.TestCase):
    def test_production_empty_whitelist_rejects_all(self):
        lua, _ = _lua_with(None)
        lua.execute('''
            _obj = _make_obj("hud_assault")
            _obj:set_visible(true)
            _result = kyohud.hud.native_visibility:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _vis = _obj:visible()
            _rejected = (_result == false)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._vis), "production must not hide unlisted objects")
        self.assertTrue(bool(g._rejected), "production acquire must return false for unlisted")


class NVAcquireReleaseTests(unittest.TestCase):
    def test_acquire_sets_visible(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_visible(true)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _vis = _obj:visible()
        ''')
        self.assertFalse(bool(lua.globals()._vis))

    def test_acquire_sets_alpha(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_alpha(1)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "alpha", value = 0.37},
            })
            _a = _obj:alpha()
        ''')
        self.assertAlmostEqual(float(lua.globals()._a), 0.37, places=2)

    def test_release_restores_prior_visible_false(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_visible(false)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            svc:release("block_a", 1)
            _vis = _obj:visible()
        ''')
        self.assertFalse(bool(lua.globals()._vis))

    def test_release_restores_prior_alpha(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_alpha(0.37)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "alpha", value = 0},
            })
            svc:release("block_a", 1)
            _a = _obj:alpha()
        ''')
        self.assertAlmostEqual(float(lua.globals()._a), 0.37, places=2)

    def test_conflict_same_object_property(self):
        lua = _svc_with_obj()
        lua.execute('''
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _result = svc:acquire("block_b", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _conflict = (_result == false)
        ''')
        self.assertTrue(bool(lua.globals()._conflict))

    def test_idempotent_reacquire(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_visible(false)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _count1 = 0
            for _ in pairs(svc._entries or {}) do _count1 = _count1 + 1 end
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _count2 = 0
            for _ in pairs(svc._entries or {}) do _count2 = _count2 + 1 end
            _vis = _obj:visible()
        ''')
        g = lua.globals()
        self.assertEqual(int(g._count1), int(g._count2),
            "idempotent reacquire must not duplicate entries")
        self.assertFalse(bool(g._vis))

    def test_generation_rollover_releases_old(self):
        lua = _svc_with_obj()
        lua.execute('''
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            svc:acquire("block_a", 2, {
                {id = _obj, property = "visible", value = false},
            })
            _vis_gen1 = true
            for _k, entry in pairs(svc._entries or {}) do
                if entry.generation == 1 then _vis_gen1 = false end
            end
        ''')
        self.assertTrue(bool(lua.globals()._vis_gen1),
                         "gen 2 must evict gen 1 entries for same owner")

    def test_release_all(self):
        lua = _svc_with_obj()
        lua.execute('''
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            svc:release_all()
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        self.assertEqual(int(lua.globals()._count), 0)

    def test_destroyed_object_no_mutate_replacement(self):
        lua = _svc_with_obj()
        lua.execute('''
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _old = _obj
            _obj._alive = false
            _new = _make_obj("hud_assault")
            svc:release("block_a", 1)
            _new_vis = _new:visible()
        ''')
        self.assertTrue(bool(lua.globals()._new_vis),
                         "release must not touch replacement object")

    def test_third_party_write_not_clobbered(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_visible(true)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _obj:set_visible(true)
            svc:release("block_a", 1)
            _vis = _obj:visible()
        ''')
        self.assertTrue(bool(lua.globals()._vis),
                         "divergent third-party write must not be overwritten")

    def test_atomic_partial_rollback(self):
        lua, _ = _lua_with('''
            _obj1 = _make_obj("a")
            _obj2 = _make_obj("b")
            _wl = { [_obj1] = {visible=true}, [_obj2] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _obj2.set_visible = function() error("setter fail") end
        ''')
        lua.execute('''
            _ok, _err = pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj1, property = "visible", value = false},
                    {id = _obj2, property = "visible", value = false},
                })
            end)
            _v1 = _obj1:visible()
        ''')
        self.assertTrue(bool(lua.globals()._v1),
                         "partial failure must roll back earlier mutations")

    def test_failed_release_retains_entry(self):
        lua = _svc_with_obj()
        lua.execute('''
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _obj.set_visible = function() error("restore fail") end
            pcall(function() svc:release("block_a", 1) end)
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        self.assertGreater(int(lua.globals()._count), 0,
                           "failed release must retain retryable entry")


class NVReleaseAllRestoresTests(unittest.TestCase):
    def test_release_all_restores_visible_false(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_visible(false)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            svc:release_all()
            _vis = _obj:visible()
        ''')
        self.assertFalse(bool(lua.globals()._vis),
            "release_all must restore original visible=false, not just drop entries")

    def test_release_all_restores_alpha_037(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_alpha(0.37)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "alpha", value = 0},
            })
            svc:release_all()
            _a = _obj:alpha()
        ''')
        self.assertAlmostEqual(float(lua.globals()._a), 0.37, places=2,
            msg="release_all must restore original alpha=0.37")

    def test_release_all_clears_entries(self):
        lua = _svc_with_obj()
        lua.execute('''
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            svc:release_all()
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        self.assertEqual(int(lua.globals()._count), 0)


class NVRollbackOwnershipTests(unittest.TestCase):
    def test_rollback_removes_ownership_entries(self):
        lua, _ = _lua_with('''
            _obj1 = _make_obj("a")
            _obj2 = _make_obj("b")
            _wl = { [_obj1] = {visible=true}, [_obj2] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _obj2.set_visible = function() error("setter fail") end
        ''')
        lua.execute('''
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj1, property = "visible", value = false},
                    {id = _obj2, property = "visible", value = false},
                })
            end)
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        self.assertEqual(int(lua.globals()._count), 0,
            "rollback after partial failure must remove all ownership entries for this acquire")


class NVAtomicPreRecordTests(unittest.TestCase):
    def test_setter_mutate_then_throw_retains_record_for_retry(self):
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _call_num = 0
            _obj.set_alpha = function(self, v)
                _call_num = _call_num + 1
                self._alpha = v
                if _call_num == 1 then
                    error("engine crash after mutation")
                end
            end
        ''')
        lua.execute('''
            _obj._alpha = 0.5
            _acq_result = svc:acquire("block_a", 1, {
                {id = _obj, property = "alpha", value = 0.0},
            })
            _a = _obj:alpha()
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
            _rel_ok = pcall(function() svc:release_all() end)
            _a2 = _obj:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._a), 0.0, places=2,
            msg="setter that mutates then throws: value stays mutated, record kept for retry")
        self.assertEqual(int(g._count), 1,
            msg="record must be retained for retry")
        self.assertAlmostEqual(float(g._a2), 0.5, places=2,
            msg="after release_all with recovered setter, original value restored")


class NVGetterFailureTests(unittest.TestCase):
    def test_getter_failure_no_silent_value_loss(self):
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _obj.alpha = function() error("getter crash") end
        ''')
        lua.execute('''
            _result = svc:acquire("block_a", 1, {
                {id = _obj, property = "alpha", value = 0.0},
            })
            _rejected = (_result == false)
        ''')
        self.assertTrue(bool(lua.globals()._rejected),
            "acquire must fail when getter errors, not silently proceed")


class NVDefectRegressionTests(unittest.TestCase):
    """RED tests exposing the four SOL defects."""

    def test_failed_setter_mutates_then_getter_errors_retains_applied_value(self):
        """Defect 1: setter mutates to requested value then getter errors => applied_value must be requested, not nil.
        Later getter recovers, third-party writes .8: release must preserve .8, not overwrite .37."""
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _call_num = 0
            _getter_ok = true
            _obj.set_alpha = function(self, v)
                _call_num = _call_num + 1
                if _call_num == 1 then
                    self._alpha = 0
                    _getter_ok = false
                    error("fail after mutation")
                end
                self._alpha = v
            end
            _obj.alpha = function(self)
                if not _getter_ok then error("getter fail") end
                return self._alpha
            end
        ''')
        lua.execute('''
            _obj._alpha = 0.5
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "alpha", value = 0.0},
                })
            end)
            _found = false
            _applied_val = nil
            for _, e in ipairs(svc._entries or {}) do
                if e.owner == "block_a" and e.generation == 1 then
                    _found = true
                    _applied_val = e.applied_value
                end
            end
            _getter_ok = true
            _obj._alpha = 0.8
            pcall(function()
                svc:release("block_a", 1)
            end)
            _final_a = _obj:alpha()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._found), "entry must be retained")
        self.assertIsNotNone(g._applied_val, "applied_value must not be nil (float(x or 0) would mask this)")
        self.assertAlmostEqual(float(g._applied_val), 0.0, places=2,
            msg="applied_value must be requested value (0.0)")
        self.assertAlmostEqual(float(g._final_a), 0.8, places=2,
            msg="release must preserve third-party write .8, not overwrite .37")

    def test_getter_error_before_setter_no_entry_inserted(self):
        """Defect 2: getter errors BEFORE setter attempt => acquire=false, #entries==0, no phantom ownership."""
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _obj.alpha = function() error("getter crash before setter") end
        ''')
        lua.execute('''
            _result = svc:acquire("block_a", 1, {
                {id = _obj, property = "alpha", value = 0.0},
            })
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._result), "acquire must return false")
        self.assertEqual(int(g._count), 0,
            "getter error before setter must not insert phantom ownership record")

    def test_userdata_throwing_index_returns_false(self):
        """Defect 3: whitelisted userdata with __index that throws => acquire returns false, doesn't throw."""
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _throwing_ud = newproxy(true)
            local mt = getmetatable(_throwing_ud)
            mt.__index = function() error("userdata __index throws") end
            _obj.alpha = _throwing_ud
        ''')
        lua.execute('''
            _ok, _result = pcall(function()
                return svc:acquire("block_a", 1, {
                    {id = _obj, property = "alpha", value = 0.0},
                })
            end)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok), "acquire must not throw even if getter lookup throws")
        self.assertFalse(bool(g._result), "acquire must return false when getter lookup throws")

    def test_production_reload_identity_and_ownership(self):
        """Defect 4: production service reload preserves identity and ownership.
        Production starts EMPTY; reload source must return same service table with entries retained."""
        lua, _ = _lua_with(None)
        lua.execute('''
            _obj = _make_obj("a")
            _obj:set_alpha(0.37)
            _wl_entry = { [_obj] = {alpha=true} }
            kyohud.hud.native_visibility._whitelist = _wl_entry
            kyohud.hud.native_visibility:acquire("block_a", 1, {
                {id = _obj, property = "alpha", value = 0},
            })
            _svc1 = kyohud.hud.native_visibility
            _a1 = _obj:alpha()
            _count1 = 0
            for _ in pairs(_svc1._entries or {}) do _count1 = _count1 + 1 end
        ''')
        lua.execute(_read(NV_PATH))
        lua.execute('''
            _svc2 = kyohud.hud.native_visibility
            _same_identity = (_svc1 == _svc2)
            _a2 = _obj:alpha()
            _count2 = 0
            for _ in pairs(_svc2._entries or {}) do _count2 = _count2 + 1 end
            _svc2:release_all()
            _a3 = _obj:alpha()
            _count3 = 0
            for _ in pairs(_svc2._entries or {}) do _count3 = _count3 + 1 end
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._same_identity),
            msg="production reload must preserve service identity")
        self.assertAlmostEqual(float(g._a1), 0.0, places=2)
        self.assertAlmostEqual(float(g._a2), 0.0, places=2,
            msg="reload must preserve active snapshot")
        self.assertEqual(int(g._count1), int(g._count2),
            msg="reload must retain entries")
        self.assertAlmostEqual(float(g._a3), 0.37, places=2,
            msg="release_all after reload must restore original")
        self.assertEqual(int(g._count3), 0, "release_all must clear entries")


class NVGenerationReleaseFailureTests(unittest.TestCase):
    def test_generation_release_failure_retains_entries(self):
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _orig_set = _obj.set_visible
            _restore_fails = false
            _obj.set_visible = function(self, v)
                if _restore_fails then error("restore fail") end
                self._vis = v
            end
            _restore_fails = true
            pcall(function()
                svc:acquire("block_a", 2, {
                    {id = _obj, property = "visible", value = false},
                })
            end)
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        self.assertGreater(int(lua.globals()._count), 0,
            "generation release failure must retain entries for retry")


class NVAcquireNoThrowTests(unittest.TestCase):
    def test_acquire_invalid_returns_false(self):
        lua, _ = _lua_with("svc = kyohud.hud.native_visibility:new({})")
        lua.execute('''
            _obj = _make_obj("hud_assault")
            _ok, _result = pcall(function()
                return svc:acquire("block_a", 1, {
                    {id = _obj, property = "visible", value = false},
                })
            end)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok),
            "acquire must not throw for invalid target")
        self.assertFalse(bool(g._result),
            "acquire on empty whitelist must return false")


class NVFiniteValidationTests(unittest.TestCase):
    def test_alpha_nan_rejected(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_alpha(1)
            _ok = pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "alpha", value = 0/0},
                })
            end)
            _a = _obj:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(float(g._a), 1.0,
            "NaN alpha must be rejected, no mutation")

    def test_alpha_infinity_rejected(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_alpha(1)
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "alpha", value = math.huge},
                })
            end)
            _a = _obj:alpha()
        ''')
        self.assertEqual(float(lua.globals()._a), 1.0,
            "Infinity alpha must be rejected, no mutation")

    def test_visible_non_bool_rejected(self):
        lua = _svc_with_obj()
        lua.execute('''
            _obj:set_visible(true)
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "visible", value = "yes"},
                })
            end)
            _vis = _obj:visible()
        ''')
        self.assertTrue(bool(lua.globals()._vis),
            "non-boolean visible must be rejected, no mutation")


class NVSetterFalseTests(unittest.TestCase):
    def test_setter_returns_false_not_recorded(self):
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _obj.set_alpha = function(self, v) return false end
        ''')
        lua.execute('''
            _ok = pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "alpha", value = 0.5},
                })
            end)
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        self.assertEqual(int(lua.globals()._count), 0,
            "setter returning false must not be recorded as success")


class NVPartialFailureRetryTests(unittest.TestCase):
    def test_partial_failure_retains_original_owner_for_retry(self):
        lua, _ = _lua_with('''
            _obj1 = _make_obj("a")
            _obj2 = _make_obj("b")
            _wl = { [_obj1] = {alpha=true}, [_obj2] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _obj2.set_visible = function() error("setter fail") end
        ''')
        lua.execute('''
            _obj1:set_alpha(0.37)
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj1, property = "alpha", value = 0},
                    {id = _obj2, property = "visible", value = false},
                })
            end)
            _a = _obj1:alpha()
        ''')
        self.assertAlmostEqual(float(lua.globals()._a), 0.37, places=2,
            msg="partial failure must restore earlier mutations to original values")

    def test_failed_rollback_retains_entry_with_original_owner(self):
        lua, _ = _lua_with('''
            _obj1 = _make_obj("a")
            _obj2 = _make_obj("b")
            _wl = { [_obj1] = {alpha=true}, [_obj2] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _obj2.set_visible = function() error("setter fail") end
            _restore_fails = false
            _orig_set_alpha = _obj1.set_alpha
            _obj1.set_alpha = function(self, v)
                if _restore_fails and v == 0.37 then error("restore fail") end
                _orig_set_alpha(self, v)
            end
        ''')
        lua.execute('''
            _obj1:set_alpha(0.37)
            _restore_fails = true
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj1, property = "alpha", value = 0},
                    {id = _obj2, property = "visible", value = false},
                })
            end)
            _found = false
            for _, e in ipairs(svc._entries or {}) do
                if e.owner == "block_a" and e.generation == 1 then
                    _found = true
                end
            end
        ''')
        self.assertTrue(bool(lua.globals()._found),
            msg="failed rollback must retain entry with ORIGINAL owner/generation for retry")


class NVConditionalOwnershipRestorationTests(unittest.TestCase):
    def test_rollback_only_restores_owned_entries(self):
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _obj:set_alpha(0.8)
            _obj.set_alpha = function(self, v)
                self._alpha = v
                error("setter fail after mutation")
            end
        ''')
        lua.execute('''
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "alpha", value = 0.0},
                })
            end)
            _a = _obj:alpha()
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._a), 0.0, places=2,
            msg="failed acquire leaves mutated value; record kept for retry, no immediate restore")
        self.assertEqual(int(g._count), 1,
            msg="record retained for retry")


class NVDuplicateRequestTests(unittest.TestCase):
    def test_duplicate_same_value_allowed(self):
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
        ''')
        lua.execute('''
            _obj:set_visible(true)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _ok = pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "visible", value = false},
                })
            end)
            _vis = _obj:visible()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok),
            "duplicate request with same value should be allowed")
        self.assertFalse(bool(g._vis))

    def test_duplicate_different_value_rejected(self):
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
        ''')
        lua.execute('''
            _obj:set_visible(true)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _ok = pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "visible", value = true},
                })
            end)
            _vis = _obj:visible()
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._vis),
            "duplicate request with different value must be rejected before mutation")


class NVSetterMutationThenThrowTests(unittest.TestCase):
    def test_setter_mutates_then_throws_retains_original_for_retry(self):
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _call_num = 0
            _restore_fails = false
            _obj.set_alpha = function(self, v)
                _call_num = _call_num + 1
                self._alpha = v
                if _call_num == 1 then
                    error("engine crash after mutation")
                end
                if _restore_fails then
                    error("restore blocked")
                end
            end
        ''')
        lua.execute('''
            _obj._alpha = 0.5
            _restore_fails = true
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "alpha", value = 0.0},
                })
            end)
            _found = false
            for _, e in ipairs(svc._entries or {}) do
                if e.owner == "block_a" and e.generation == 1 and e.old_value == 0.5 then
                    _found = true
                end
            end
        ''')
        self.assertTrue(bool(lua.globals()._found),
            "setter that mutates then throws must retain ORIGINAL owner/generation snapshot for retry")

    def test_setter_changes_to_8_then_fails_two_request(self):
        """SOL extra: p setter changes o alpha to .8 then fails during two-request acquire => .8 preserved"""
        lua, _ = _lua_with('''
            _obj1 = _make_obj("a")
            _obj2 = _make_obj("b")
            _wl = { [_obj1] = {alpha=true}, [_obj2] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
        ''')
        lua.execute('''
            _obj1._alpha = 1.0
            _obj2._alpha = 1.0
            _call_num = 0
            _obj1.set_alpha = function(self, v)
                _call_num = _call_num + 1
                self._alpha = v
                if _call_num == 1 then
                    self._alpha = 0.8
                    error("fail after setting to .8")
                end
            end
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj1, property = "alpha", value = 0.0},
                    {id = _obj2, property = "alpha", value = 0.0},
                })
            end)
            _a = _obj1:alpha()
        ''')
        self.assertAlmostEqual(float(lua.globals()._a), 0.8, places=2,
            msg="setter that changes to .8 then fails must preserve .8")

    def test_failed_setter_mutates_to_0_then_getter_fails(self):
        """SOL extra: failed setter mutates to 0 then makes getter fail => retained original snapshot"""
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {alpha=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            _call_num = 0
            _getter_ok = true
            _obj.set_alpha = function(self, v)
                _call_num = _call_num + 1
                if _call_num == 1 then
                    self._alpha = 0
                    _getter_ok = false
                    error("fail after mutation")
                end
                self._alpha = v
            end
            _obj.alpha = function(self)
                if not _getter_ok then error("getter fail") end
                return self._alpha
            end
        ''')
        lua.execute('''
            _obj._alpha = 0.5
            pcall(function()
                svc:acquire("block_a", 1, {
                    {id = _obj, property = "alpha", value = 0.0},
                })
            end)
            _found = false
            for _, e in ipairs(svc._entries or {}) do
                if e.owner == "block_a" and e.generation == 1 and e.old_value == 0.5 then
                    _found = true
                end
            end
            _getter_ok = true
            pcall(function()
                svc:release("block_a", 1)
            end)
            _a = _obj:alpha()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._found),
            msg="must retain original snapshot even when getter fails")
        self.assertAlmostEqual(float(g._a), 0.5, places=2,
            msg="after getter/setter recover, release must restore original")


class NVGetterReleaseFailureTests(unittest.TestCase):
    def test_getter_missing_on_release_retains_entry(self):
        """SOL extra: getter missing on release => retain entry"""
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
            svc:acquire("block_a", 1, {
                {id = _obj, property = "visible", value = false},
            })
            _obj.visible = nil
            pcall(function() svc:release("block_a", 1) end)
            _count = 0
            for _ in pairs(svc._entries or {}) do _count = _count + 1 end
        ''')
        self.assertGreater(int(lua.globals()._count), 0,
            "getter missing on release must retain entry for retry")


class NVMalformedRequestTests(unittest.TestCase):
    def test_malformed_request_scalar_returns_false(self):
        """SOL extra: malformed request scalar => false no throw"""
        lua, _ = _lua_with('''
            _obj = _make_obj("a")
            _wl = { [_obj] = {visible=true} }
            svc = kyohud.hud.native_visibility:new(_wl)
        ''')
        lua.execute('''
            _ok, _result = pcall(function()
                return svc:acquire("block_a", 1, "not a table")
            end)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok),
            "malformed request must not throw")
        self.assertFalse(bool(g._result),
            "malformed request must return false")


class VisibilityAcceptanceTests(unittest.TestCase):
    def test_actual_production_service_empty_and_callable(self):
        l = acceptance_env()
        l.execute('''
            local p=kyohud.hud.native_visibility
            assert(type(p._whitelist)=='table' and next(p._whitelist)==nil,'production not initialized empty')
            local o=obj()
            assert(p:acquire('a',1,{{id=o,property='visible',value=false}})==false)
            assert(o.v and o.a==.37)
        ''')

    def test_release_all_retry_preserves_snapshot(self):
        l = acceptance_env()
        l.execute('''
            local o=obj()
            local s=kyohud.hud.native_visibility:new({[o]={alpha=true,visible=true}})
            assert(s:acquire('a',1,{{id=o,property='alpha',value=0}}))
            o.set_alpha=function() error('restore blocked') end
            s:release_all()
            assert(#s._entries==1,'release_all discarded failed restoration')
            o.set_alpha=function(self,v) self.a=v end
            s:release_all();assert(o.a==.37 and #s._entries==0)
        ''')

    def test_getter_error_during_release_keeps_retry(self):
        l = acceptance_env()
        l.execute('''
            local o=obj()
            local s=kyohud.hud.native_visibility:new({[o]={alpha=true,visible=true}})
            assert(s:acquire('a',1,{{id=o,property='alpha',value=0}}))
            o.alpha=function() error('read blocked') end;s:release('a',1)
            assert(#s._entries==1,'getter failure discarded ownership')
            o.alpha=function(self) return self.a end;s:release('a',1)
            assert(o.a==.37 and #s._entries==0)
        ''')

    def test_failed_acquire_and_failed_rollback_keeps_retry(self):
        l = acceptance_env()
        l.execute('''
            local o=obj()
            local s=kyohud.hud.native_visibility:new({[o]={alpha=true,visible=true}})
            local first=true
            o.set_alpha=function(self,v)
             if first then self.a=v;first=false;error('mutated then failed') end
             error('restore blocked')
            end
            assert(s:acquire('a',1,{{id=o,property='alpha',value=0}})==false)
            assert(o.a==0 and #s._entries==1,'lost partially applied failed setter')
            o.set_alpha=function(self,v) self.a=v end;s:release_all()
            assert(o.a==.37 and #s._entries==0)
        ''')

    def test_generation_rollover_restore_failure_aborts(self):
        l = acceptance_env()
        l.execute('''
            local o=obj()
            local s=kyohud.hud.native_visibility:new({[o]={alpha=true,visible=true}})
            assert(s:acquire('a',1,{{id=o,property='alpha',value=0}}))
            o.set_alpha=function() error('restore blocked') end
            assert(s:acquire('a',2,{{id=o,property='visible',value=false}})==false,'new generation while old restore blocked')
            assert(o.v and #s._entries==1 and s._entries[1].generation==1)
        ''')

    def test_destroyed_target_rejected(self):
        l = acceptance_env()
        l.execute('''
            local o=obj()
            local s=kyohud.hud.native_visibility:new({[o]={alpha=true,visible=true}})
            o.live=false;assert(s:acquire('a',1,{{id=o,property='alpha',value=0}})==false);assert(o.a==.37)
        ''')

    def test_reacquire_does_not_ignore_different_write(self):
        l = acceptance_env()
        l.execute('''
            local o=obj()
            local s=kyohud.hud.native_visibility:new({[o]={alpha=true,visible=true}})
            assert(s:acquire('a',1,{{id=o,property='alpha',value=0}}))
            assert(s:acquire('a',1,{{id=o,property='alpha',value=.2}})==false,'different reacquire silently accepted')
            assert(o.a==0);s:release_all();assert(o.a==.37)
        ''')

    def test_partial_acquire_rolls_back_and_frees_owner(self):
        l = acceptance_env()
        l.execute('''
            local o=obj();local p=obj()
            local s=kyohud.hud.native_visibility:new({[o]={alpha=true},[p]={visible=true}})
            p.set_visible=function() error('fail') end
            assert(s:acquire('a',1,{{id=o,property='alpha',value=0},{id=p,property='visible',value=false}})==false)
            assert(o.a==.37 and #s._entries==0)
            assert(s:acquire('b',1,{{id=o,property='alpha',value=0}}))
            s:release_all();assert(o.a==.37)
        ''')


class NVSetterMutateUnrelatedValueTests(unittest.TestCase):
    def test_setter_mutates_to_unrelated_value_then_fails_applied_not_contaminated(self):
        """SOL (4): setter changes alpha to .8 (not requested 0, not original .37) then fails.
        applied_value must be 0 (the requested value). Release must preserve .8 (not overwrite with .37).
        Regression: getter failure during release retains entry; restore getter, retry release restores original .37, entries empty."""
        l = acceptance_env()
        l.execute('''
        local o=obj()
        local s=kyohud.hud.native_visibility:new({[o]={alpha=true}})
        o.a=.37
        local call_num=0
        o.set_alpha=function(self,v)
            call_num=call_num+1
            if call_num==1 then
                self.a=0.8
                error('fail after setting to .8')
            end
            self.a=v
        end
        pcall(function()
            s:acquire('a',1,{{id=o,property='alpha',value=0}})
        end)
        local found=false
        local applied_val=nil
        for _,e in ipairs(s._entries or {}) do
            if e.owner=='a' and e.generation==1 then
                found=true
                applied_val=e.applied_value
            end
        end
        assert(found,'entry must be retained')
        assert(applied_val==0,'applied_value must be requested value 0, got '..tostring(applied_val))
        o.set_alpha=function(self,v) self.a=v end
        pcall(function() s:release('a',1) end)
        assert(o.a==0.8,'release must preserve .8, not overwrite with .37, got '..tostring(o.a))
        local o2=obj()
        local s2=kyohud.hud.native_visibility:new({[o2]={alpha=true}})
        o2.a=.37
        assert(s2:acquire('b',1,{{id=o2,property='alpha',value=0}}))
        assert(o2.a==0)
        o2.alpha=function() error('getter crash during release') end
        s2:release('b',1)
        local c=0
        for _ in pairs(s2._entries or {}) do c=c+1 end
        assert(c>0,'getter failure during release must retain entry, got '..tostring(c))
        o2.alpha=function(self) return self.a end
        s2:release('b',1)
        assert(o2.a==.37,'release must restore original .37, got '..tostring(o2.a))
        local c2=0
        for _ in pairs(s2._entries or {}) do c2=c2+1 end
        assert(c2==0,'entries must be empty after successful release, got '..tostring(c2))
        ''')


class NVSilentNoopSetterTests(unittest.TestCase):
    def test_release_setter_silent_noop_retains_entry_then_retry_restores(self):
        """SOL (5): restoration setter silently does nothing (no error, no mutation).
        Entry must be retained for retry. Once setter restored, release restores .37."""
        l = acceptance_env()
        l.execute('''
        local o=obj()
        local s=kyohud.hud.native_visibility:new({[o]={alpha=true}})
        o.a=.37
        assert(s:acquire('a',1,{{id=o,property='alpha',value=0}}))
        assert(o.a==0)
        o.set_alpha=function(self,v) end
        s:release('a',1)
        local count=0
        for _ in pairs(s._entries or {}) do count=count+1 end
        assert(count==1,'silent no-op release must retain entry for retry, got '..tostring(count))
        o.set_alpha=function(self,v) self.a=v end
        s:release('a',1)
        assert(o.a==.37,'after setter restored, release must restore .37, got '..tostring(o.a))
        ''')

    def test_silent_noop_acquire_then_reacquire_no_false_success(self):
        """SOL (6): acquire with silent no-op setter returns false.
        Reacquire must also return false (no false success).
        Once setter restored and stale entries cleared, acquire/release work."""
        l = acceptance_env()
        l.execute('''
        local o=obj()
        local s=kyohud.hud.native_visibility:new({[o]={alpha=true}})
        o.a=.37
        o.set_alpha=function(self,v) end
        local r1=s:acquire('a',1,{{id=o,property='alpha',value=0}})
        assert(r1==false,'first acquire must return false')
        local r2=s:acquire('a',1,{{id=o,property='alpha',value=0}})
        assert(r2==false,'reacquire with no-op setter must also return false, not silent success')
        o.set_alpha=function(self,v) self.a=v end
        s:release_all()
        local r3=s:acquire('a',1,{{id=o,property='alpha',value=0}})
        assert(r3==true,'acquire with restored setter must succeed')
        assert(o.a==0)
        s:release('a',1)
        assert(o.a==.37,'release must restore .37')
        ''')


class NVUserdataAuthorityTests(unittest.TestCase):
    def test_userdata_with_raising_index_whitelisted_no_throw(self):
        """SOL (7): userdata itself whitelisted with __index that raises.
        alive override for ud prevents fake alive x.live from raising before the real getter test."""
        l = acceptance_env()
        l.execute('''
        local ud=newproxy(true)
        local mt=getmetatable(ud)
        mt.__index=function() error('userdata __index throws') end
        local orig_alive=alive
        alive=function(x) if x==ud then return true end return orig_alive(x) end
        local s=kyohud.hud.native_visibility:new({[ud]={alpha=true,visible=true}})
        local ok,result=pcall(function()
            return s:acquire('a',1,{{id=ud,property='alpha',value=0}})
        end)
        assert(ok,'acquire must not throw even when userdata __index raises')
        assert(result==false,'acquire must return false when getter lookup fails')
        alive=orig_alive
        ''')

    def test_alive_global_is_authority_for_userdata(self):
        """SOL (8): global alive returning true for userdata is the sole authority.
        Private state a=.37 outside userdata; __index accepts ONLY alpha/set_alpha and errors on any other key.
        debug.getmetatable temporarily replaced by a counting error function.
        Acquire then release must succeed and restore .37. introspection_calls must be 0."""
        l = acceptance_env()
        l.execute('''
        local ud=newproxy(true)
        local mt=getmetatable(ud)
        local a=.37
        mt.__index=function(self,key)
            if key=='alpha' then return function() return a end end
            if key=='set_alpha' then return function(_,v) a=v end end
            error('no access to key: '..tostring(key))
        end
        mt.__newindex=function() error('cannot set fields on userdata') end
        local orig_alive=alive
        alive=function(x) if x==ud then return true end return orig_alive(x) end
        local introspection_calls=0
        local orig_gm=debug.getmetatable
        debug.getmetatable=function()
            introspection_calls=introspection_calls+1
            error('introspection not allowed')
        end
        local s=kyohud.hud.native_visibility:new({[ud]={alpha=true}})
        local ok1,result1=pcall(function()
            return s:acquire('a',1,{{id=ud,property='alpha',value=0}})
        end)
        assert(ok1,'acquire must not throw')
        assert(result1==true,'acquire must succeed when alive says userdata is alive')
        assert(a==0,'acquire must mutate alpha to 0')
        local ok2=pcall(function() s:release('a',1) end)
        assert(ok2,'release must succeed')
        assert(a==.37,'release must restore original .37')
        debug.getmetatable=orig_gm
        assert(introspection_calls==0,'alive must be sole authority, no debug.getmetatable calls, got '..tostring(introspection_calls))
        alive=orig_alive
        ''')


class NVRedRegressionTests(unittest.TestCase):
    """RED tests from SOL final review — four additional defects, NO production fix in this pass."""

    def test_red_a_setter_mutates_then_getter_disappears_entry_retained(self):
        """RED (a): setter writes value then destroys getter. acquire=false but entry retained.
        Restore getter+setter, release restores .37, entries cleared."""
        l = acceptance_env()
        l.execute('''
        local o=obj()
        o.a=.37
        o.set_alpha=function(self,v) self.a=v; self.alpha=nil end
        local s=kyohud.hud.native_visibility:new({[o]={alpha=true}})
        local r1=s:acquire('a',1,{{id=o,property='alpha',value=0}})
        assert(r1==false,'acquire must return false when getter disappears after mutation')
        local count1=0
        for _ in pairs(s._entries or {}) do count1=count1+1 end
        assert(count1==1,'entry must be retained with old .37 requested 0, got '..tostring(count1))
        local e=s._entries[1]
        assert(e.old_value==.37,'old_value must be .37, got '..tostring(e.old_value))
        assert(e.applied_value==0,'applied_value must be 0, got '..tostring(e.applied_value))
        o.alpha=function(self) return self.a end
        o.set_alpha=function(self,v) self.a=v end
        s:release('a',1)
        assert(o.a==.37,'after getter/setter restored, release must restore .37, got '..tostring(o.a))
        local count2=0
        for _ in pairs(s._entries or {}) do count2=count2+1 end
        assert(count2==0,'entries cleared after successful release, got '..tostring(count2))
        ''')

    def test_red_b_setter_destroys_getter_without_mutating_release_retains(self):
        """RED (b): release setter destroys getter without actually mutating value.
        Entry retained. Restore getter+setter, retry release restores .37."""
        l = acceptance_env()
        l.execute('''
        local o=obj()
        o.a=.37
        local s=kyohud.hud.native_visibility:new({[o]={alpha=true}})
        assert(s:acquire('a',1,{{id=o,property='alpha',value=0}}))
        assert(o.a==0)
        o.set_alpha=function(self,v) self.alpha=nil end
        s:release('a',1)
        local count1=0
        for _ in pairs(s._entries or {}) do count1=count1+1 end
        assert(count1==1,'entry must be retained when restore setter destroys getter without mutating, got '..tostring(count1))
        o.alpha=function(self) return self.a end
        o.set_alpha=function(self,v) self.a=v end
        s:release('a',1)
        assert(o.a==.37,'after getter/setter restored, release must restore .37, got '..tostring(o.a))
        local count2=0
        for _ in pairs(s._entries or {}) do count2=count2+1 end
        assert(count2==0,'entries cleared after successful restore, got '..tostring(count2))
        ''')

    def test_red_c_visible_false_to_false_release_must_clear_entry(self):
        """RED (c): original visible=false, requested visible=false.
        Acquire then release must clear entry. readback==old is success even if old==applied."""
        l = acceptance_env()
        l.execute('''
        local o=obj()
        o.v=false
        local s=kyohud.hud.native_visibility:new({[o]={visible=true}})
        assert(s:acquire('a',1,{{id=o,property='visible',value=false}}))
        assert(o.v==false)
        s:release('a',1)
        local count=0
        for _ in pairs(s._entries or {}) do count=count+1 end
        assert(count==0,'release must clear entry when old==applied==false, got '..tostring(count))
        ''')


if __name__ == "__main__":
    unittest.main()
