"""LOT2b -- objectives manifest loading end-to-end (RED).

Single compact test: actual mod.txt must declare exactly 3 objectives hook
entries (lib/managers/hud/hudobjectives, lib/managers/objectivesmanager,
lib/managers/hudmanagerpd2). Per-context loading iterates actual manifest
hooks matching each context with lua/hud/ prefix (no hardcoded HUD_SUBGRAPH).

Exercises: EARLY hudobjectives context (runtime nil, 5 HUDObjectives hooks),
OM context (7 OM hooks), HUD context (runtime loaded, 2 HUD hooks), repeated
context idempotence, unknown context no registrations, shared identity,
positive lifecycle (real init_finalize + OM activation -> owned title),
transition replace (real new init_finalize + update -> old 8 native leaves
restored, no old owner refs, O root under current RT root, data snapshot
current, stale manager real destroy cannot tear new root).

RED: current mod.txt lacks objectives entries.
"""
import json
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

from test_hud_objectives import (
    STUBS, DIESEL, ROOT, OBJECTIVES_PATH,
    LAYOUT_PATH, NATIVE_VIS_PATH, RUNTIME_PATH, MISSION_PATH,
)
from test_hud_objectives_visibility import NATIVE_HUD_OBJECTIVES_FIXTURE


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _read_required(p):
    src = _read(p)
    assert src is not None, "missing required file: " + str(p)
    return src


class ObjectivesManifestLoadingTests(unittest.TestCase):

    def test_manifest_declares_objectives_and_loading_activates(self):
        meta = json.loads(
            (ROOT / "mod.txt").read_text(encoding="utf-8-sig")
        )
        hooks = meta["hooks"]

        obj_hooks = [h for h in hooks if h["script_path"] == "lua/hud/objectives.lua"]
        self.assertEqual(len(obj_hooks), 3,
            "mod.txt must have exactly 3 objectives entries, got "
            + str(len(obj_hooks)))

        expected_contexts = {
            "lib/managers/hud/hudobjectives",
            "lib/managers/objectivesmanager",
            "lib/managers/hudmanagerpd2",
        }
        actual_contexts = {h["hook_id"] for h in obj_hooks}
        self.assertEqual(actual_contexts, expected_contexts,
            "objectives hook_ids must be " + str(sorted(expected_contexts))
            + ", got " + str(sorted(actual_contexts)))

        hudmanager_scripts = [
            h["script_path"] for h in hooks
            if h["hook_id"] == "lib/managers/hudmanagerpd2"
        ]
        self.assertIn("lua/hud/objectives.lua", hudmanager_scripts,
            "objectives must appear in hudmanagerpd2 scripts")
        self.assertIn("lua/hud/runtime.lua", hudmanager_scripts,
            "runtime must appear in hudmanagerpd2 scripts")
        self.assertIn("lua/hud/mission.lua", hudmanager_scripts,
            "mission must appear in hudmanagerpd2 scripts")
        obj_idx = hudmanager_scripts.index("lua/hud/objectives.lua")
        rt_idx = hudmanager_scripts.index("lua/hud/runtime.lua")
        mi_idx = hudmanager_scripts.index("lua/hud/mission.lua")
        self.assertGreater(obj_idx, rt_idx,
            "objectives must come after runtime in hudmanagerpd2")
        self.assertGreater(obj_idx, mi_idx,
            "objectives must come after mission in hudmanagerpd2")

        def scripts_for_context(context):
            return [
                h["script_path"] for h in hooks
                if h["hook_id"] == context
                and h["script_path"].startswith("lua/hud/")
            ]

        early_scripts = scripts_for_context("lib/managers/hud/hudobjectives")
        om_scripts = scripts_for_context("lib/managers/objectivesmanager")
        hud_scripts = scripts_for_context("lib/managers/hudmanagerpd2")

        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute(STUBS)
        lua.execute(DIESEL)
        lua.execute(NATIVE_HUD_OBJECTIVES_FIXTURE)

        lua.execute(r'''
            local orig_make_panel = _make_panel
            function _make_panel(name)
                local p = orig_make_panel(name)
                p._stopped = false
                p._animated = false
                p._set_h_calls = {}
                p._set_w_calls = {}
                p._animate_calls = {}
                p._scheduled_fn = nil
                p._scheduled_args = nil
                function p:stop()
                    self._stopped = true
                    self._scheduled_fn = nil
                    self._scheduled_args = nil
                end
                function p:animate(fn, ...)
                    self._animated = true
                    self._scheduled_fn = fn
                    self._scheduled_args = {...}
                    table.insert(self._animate_calls, fn)
                end
                function p:set_h(h) self._h = h; table.insert(self._set_h_calls, h) end
                function p:set_w(w) self._w = w; table.insert(self._set_w_calls, w) end
                function p:set_y(y) self._y = y end
                local orig_text = p.text
                p.text = function(self, opts)
                    local t = orig_text(self, opts)
                    t._stopped = false
                    t._animated = false
                    t._set_h_calls = {}
                    t._set_w_calls = {}
                    t._scheduled_fn = nil
                    t._scheduled_args = nil
                    function t:stop()
                        self._stopped = true
                        self._scheduled_fn = nil
                        self._scheduled_args = nil
                    end
                    function t:animate(fn, ...)
                        self._animated = true
                        self._scheduled_fn = fn
                        self._scheduled_args = {...}
                    end
                    function t:set_h(h) self._h = h; table.insert(self._set_h_calls, h) end
                    function t:set_w(w) self._w = w; table.insert(self._set_w_calls, w) end
                    function t:set_y(y) self._y = y end
                    return t
                end
                return p
            end
        ''')

        lua.execute(r'''
            local _orig_hud_activate = HUDManager.activate_objective
            HUDManager.activate_objective = function(self, data)
                _orig_hud_activate(self, data)
                if self._hud_objectives and type(self._hud_objectives.activate_objective) == "function" then
                    self._hud_objectives:activate_objective(data)
                end
            end
            local _orig_hud_update_amount = HUDManager.update_amount_objective
            HUDManager.update_amount_objective = function(self, data)
                _orig_hud_update_amount(self, data)
                if self._hud_objectives and type(self._hud_objectives.update_amount_objective) == "function" then
                    self._hud_objectives:update_amount_objective(data)
                end
            end
            local _orig_hud_complete = HUDManager.complete_objective
            HUDManager.complete_objective = function(self, data)
                _orig_hud_complete(self, data)
                if self._hud_objectives and type(self._hud_objectives.complete_objective) == "function" then
                    self._hud_objectives:complete_objective(data)
                end
            end
        ''')

        lua.execute("_init_fp = _make_parent(); _make_mgr(_init_fp)")

        lua.execute('RequiredScript = "lib/managers/hud/hudobjectives"')
        for script_path in early_scripts:
            lua.execute(_read_required(ROOT / script_path))

        lua.execute(r'''
            assert(kyohud.hud.runtime == nil,
                "runtime must be nil in early hudobjectives context")
            assert(kyohud.hud.objectives ~= nil, "O must exist after early context")
            _early_O_id = tostring(kyohud.hud.objectives)
            _early_active_ref = kyohud.hud.objectives._active
            _early_sentinel_ref = kyohud.hud.objectives._load_order_sentinel
            _early_sentinel_value = kyohud.hud.objectives._load_order_sentinel.value
        ''')

        lua.execute('RequiredScript = "lib/managers/objectivesmanager"')
        for script_path in om_scripts:
            lua.execute(_read_required(ROOT / script_path))

        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        for script_path in hud_scripts:
            lua.execute(_read_required(ROOT / script_path))

        hooks_after_first_hud = len(list(lua.eval("Hooks._all").items()))

        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        for script_path in hud_scripts:
            lua.execute(_read_required(ROOT / script_path))

        hooks_after_repeated = len(list(lua.eval("Hooks._all").items()))

        lua.execute(r'''
            _pre_unknown_count = #Hooks._all
            RequiredScript = "lib/managers/unknown_context_xyz"
        ''')
        lua.execute(_read_required(OBJECTIVES_PATH))
        lua.execute(r'''
            _post_unknown_count = #Hooks._all
        ''')

        lua.execute(r'''
            _ids = {}
            _dupes = 0
            for _, e in ipairs(Hooks._all) do
                if _ids[e.id] then _dupes = _dupes + 1 end
                _ids[e.id] = true
            end

            _hudobj_count = 0
            _hudobj_methods = {}
            _hudobj_kinds = {}
            _hudobj_ids = {}
            for _, e in ipairs(Hooks._all) do
                if e.id and e.id:find("HUDObj") then
                    _hudobj_count = _hudobj_count + 1
                    _hudobj_methods[_hudobj_count] = e.method
                    _hudobj_kinds[_hudobj_count] = e.kind
                    _hudobj_ids[_hudobj_count] = e.id
                end
            end

            _om_count = 0
            _om_ids = {}
            for _, e in ipairs(Hooks._all) do
                if e.id and e.id:find("KyohUD_OM_") then
                    _om_count = _om_count + 1
                    _om_ids[_om_count] = e.id
                end
            end

            _hud_obj_count = 0
            _hud_obj_ids = {}
            for _, e in ipairs(Hooks._all) do
                if e.id and e.id:find("KyohUD_HUD_") then
                    _hud_obj_count = _hud_obj_count + 1
                    _hud_obj_ids[_hud_obj_count] = e.id
                end
            end

            assert(rawequal(kyohud, Kyosh1roHUD), "shared identity")
            assert(kyohud.hud.objectives ~= nil, "O must exist")
            assert(tostring(kyohud.hud.objectives) == _early_O_id,
                "O identity must survive across contexts")
            assert(kyohud.hud.objectives._active == _early_active_ref,
                "O._active sentinel identity must survive across contexts")
            assert(type(kyohud.hud.objectives._active) == "table",
                "O._active sentinel must be nonempty table")
            assert(kyohud.hud.objectives._load_order_sentinel == _early_sentinel_ref,
                "O._load_order_sentinel reference must survive across contexts")
            assert(kyohud.hud.objectives._load_order_sentinel.value == 17,
                "O._load_order_sentinel.value must be 17 after all loads")

            _all_triples = {}
            _all_count = 0
            for _, e in ipairs(Hooks._all) do
                _all_count = _all_count + 1
                _all_triples[_all_count] = {e.kind, e.method, e.id}
            end

            _expected_triples = {
                {"pre", "activate_objective", "KyohUD_HUDObj_ActivateObjective_Pre"},
                {"pre", "open_right_done", "KyohUD_HUDObj_OpenRightDone_Pre"},
                {"post", "open_right_done", "KyohUD_HUDObj_OpenRightDone_Post"},
                {"pre", "complete_objective", "KyohUD_HUDObj_CompleteObjective_Pre"},
                {"post", "_animate_complete_objective", "KyohUD_HUDObj_AnimateComplete_Post"},
                {"post", "HUDBGBox_animate_close_right", "KyohUD_HUDObj_CloseRight_Post"},
                {"post", "activate_objective", "KyohUD_OM_ActivateObjective"},
                {"post", "activate_objective_countdown", "KyohUD_OM_ActivateObjectiveCountdown"},
                {"post", "remove_objective", "KyohUD_OM_RemoveObjective"},
                {"post", "complete_objective", "KyohUD_OM_CompleteObjective"},
                {"post", "complete_objective_countdown", "KyohUD_OM_CompleteObjectiveCountdown"},
                {"post", "complete_sub_objective", "KyohUD_OM_CompleteSubObjective"},
                {"post", "reset", "KyohUD_OM_Reset"},
                {"post", "init_finalize", "KyohHUD_Runtime_InitFinalize"},
                {"post", "_setup_player_info_hud_pd2", "KyohHUD_Runtime_SetupPlayerInfo"},
                {"post", "resolution_changed", "KyohHUD_Runtime_ResolutionChanged"},
                {"post", "update", "KyohHUD_Runtime_Update"},
                {"pre", "destroy", "KyohHUD_Runtime_Destroy"},
                {"post", "activate_objective", "KyohUD_HUD_ActivateObjective"},
                {"post", "complete_objective", "KyohUD_HUD_CompleteObjective"},
            }
            _expected_count = #_expected_triples

            assert(_all_count == _expected_count,
                "COMPLETE Hooks._all count must be " .. _expected_count .. ", got " .. _all_count)

            _found_set = {}
            for i = 1, _all_count do
                local t = _all_triples[i]
                _found_set[t[3]] = {t[1], t[2]}
            end
            for i = 1, _expected_count do
                local exp = _expected_triples[i]
                local f = _found_set[exp[3]]
                assert(f ~= nil, "missing expected hook id: " .. exp[3])
                assert(f[1] == exp[1], "kind mismatch for " .. exp[3] .. ": expected " .. exp[1] .. " got " .. f[1])
                assert(f[2] == exp[2], "method mismatch for " .. exp[3] .. ": expected " .. exp[2] .. " got " .. f[2])
            end
        ''')

        self.assertEqual(int(lua.globals()._dupes), 0,
            "no duplicate hooks across repeated context execution")
        self.assertEqual(hooks_after_repeated, hooks_after_first_hud,
            "repeated HUD context must not add extra hooks")
        self.assertEqual(int(lua.globals()._post_unknown_count),
            int(lua.globals()._pre_unknown_count),
            "unknown context must not register any hooks")
        self.assertEqual(int(lua.globals()._hudobj_count), 6,
            "exactly 6 early HUDObjectives registrations, got "
            + str(int(lua.globals()._hudobj_count)))
        self.assertEqual(int(lua.globals()._om_count), 7,
            "exactly 7 OM hooks, got " + str(int(lua.globals()._om_count)))
        self.assertEqual(int(lua.globals()._hud_obj_count), 2,
            "exactly 2 HUD objective callbacks, got "
            + str(int(lua.globals()._hud_obj_count)))

        hudobj_ids_list = [str(lua.globals()["_hudobj_ids"][i]) for i in range(1, 7)]
        self.assertIn("KyohUD_HUDObj_ActivateObjective_Pre", hudobj_ids_list)
        self.assertIn("KyohUD_HUDObj_OpenRightDone_Pre", hudobj_ids_list)
        self.assertIn("KyohUD_HUDObj_OpenRightDone_Post", hudobj_ids_list)
        self.assertIn("KyohUD_HUDObj_CompleteObjective_Pre", hudobj_ids_list)
        self.assertIn("KyohUD_HUDObj_AnimateComplete_Post", hudobj_ids_list)
        self.assertIn("KyohUD_HUDObj_CloseRight_Post", hudobj_ids_list)

        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local source_hud_panel = _make_panel("source_hud_panel")
            source_hud_panel._w = 1920; source_hud_panel._h = 1080
            local objectives_panel = source_hud_panel:panel({
                name = "objectives_panel", x = 0, y = 0, w = 500, h = 100, visible = true,
            })
            objectives_panel._alpha = 1

            local icon_objectivebox = objectives_panel:text({
                name = "icon_objectivebox", x = 0, y = 0, w = 24, h = 24, visible = true,
            })
            icon_objectivebox._alpha = 0.37

            local objective_text = objectives_panel:text({
                name = "objective_text", x = 34, y = 6, w = 180, h = 20,
                text = "Collect bags", visible = true,
            })
            objective_text._alpha = 0.37

            local amount_text = objectives_panel:text({
                name = "amount_text", x = 34, y = 24, w = 180, h = 20,
                text = "0/3", visible = true,
            })
            amount_text._alpha = 0.37

            local bg_box = objectives_panel:panel({
                name = "test_bg_box", x = 26, y = 0, w = 200, h = 38, visible = true,
            })
            bg_box._alpha = 1

            local bg = bg_box:text({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = true})
            bg._alpha = 0.37
            local left_top = bg_box:text({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
            left_top._alpha = 0.37
            local left_bottom = bg_box:text({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
            left_bottom._alpha = 0.37
            local right_top = bg_box:text({name = "right_top", x = 192, y = 0, w = 8, h = 8, visible = true})
            right_top._alpha = 0.37
            local right_bottom = bg_box:text({name = "right_bottom", x = 192, y = 30, w = 8, h = 8, visible = true})
            right_bottom._alpha = 0.37

            local leaves = {
                icon_objectivebox, objective_text, amount_text,
                bg, left_top, left_bottom, right_top, right_bottom,
            }
            local originals = {}
            for i, leaf in ipairs(leaves) do
                originals[i] = {visible = leaf:visible(), alpha = leaf:alpha()}
            end

            local native_obj = setmetatable({}, HUDObjectives)
            native_obj:init({panel = source_hud_panel})
            native_obj._bg_box = bg_box
            managers.hud._hud_objectives = native_obj

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect", text = "Collect bags", amount = 3,
                current_amount = 0, sub_objectives = {},
            }

            local RT = kyohud.hud.runtime
            local O = kyohud.hud.objectives

            managers.hud:init_finalize()

            OM:activate_objective("collect", nil, {amount = 3})

            native_obj:open_right_done(true)

            RT:update(managers.hud, 1.0, 0.016)

            assert(O._mounted == true, "O must be mounted after lifecycle")
            assert(O._root_panel and O._root_panel._alive, "O root must be alive")
            assert(#O._active == 1, "O._active must have 1 entry, got " .. #O._active)
            assert(O._active[1].id == "collect", "active id must be collect")
            assert(O._active[1].text == "Collect bags", "active text must match")

            local title_prim = O._slot_prims[1] and O._slot_prims[1].text
            assert(title_prim, "title primitive must exist")
            assert(title_prim:text() == "Collect bags",
                "title must display 'Collect bags', got '" .. title_prim:text() .. "'")

            assert(managers.hud._hud_objectives._active_objective_id == "collect",
                "native active id must be set by HUDObjectives:activate_objective forwarding")

            _old_root = O._root_panel
            _old_mgr = managers.hud
            _old_O_manager = O._manager
            _old_active_id = O._active[1].id
            _old_active_text = O._active[1].text
            _old_native_gen = O._native_generation

            _old_leaf_originals = {}
            for i, leaf in ipairs(leaves) do
                _old_leaf_originals[i] = {visible = leaf:visible(), alpha = leaf:alpha()}
            end

            local new_fp = _make_parent()
            local new_safe = _make_mgr(new_fp)
            local new_mgr = managers.hud

            managers.hud:init_finalize()

            RT:update(new_mgr, 2.0, 0.016)

            assert(O._manager == new_mgr,
                "O must be bound to current manager after transition, got "
                .. tostring(O._manager))
            assert(O._root_panel and O._root_panel._alive,
                "O root must be alive under current RT root")
            assert(O._root_panel:parent() == RT._root_panel,
                "new O root parent must be RT._root_panel")
            assert(#O._active == 1, "data snapshot must be current, got " .. #O._active)
            assert(O._active[1].id == _old_active_id,
                "snapshot id must be preserved")
            assert(O._active[1].text == _old_active_text,
                "snapshot text must be preserved")

            local old_owner_remaining = 0
            local nv = kyohud.hud.native_visibility
            if nv then
                for _, e in ipairs(nv._entries) do
                    if e.owner == O then
                        old_owner_remaining = old_owner_remaining + 1
                    end
                end
            end
            assert(old_owner_remaining == 0,
                "no old owner NV refs after transition to new manager without native, got "
                .. old_owner_remaining)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == originals[i].visible,
                    "old leaf " .. i .. " must be restored to original visible after transition, got "
                    .. tostring(leaf:visible()))
                assert(leaf:alpha() == originals[i].alpha,
                    "old leaf " .. i .. " alpha must remain original after transition")
            end

            _old_mgr:destroy()

            assert(O._root_panel and O._root_panel._alive,
                "stale manager destroy must not tear new root")
            assert(O._manager == new_mgr,
                "O must still be bound to current manager after stale destroy")
            assert(#O._active == 1,
                "data snapshot must survive stale destroy")
        ''')


if __name__ == "__main__":
    unittest.main()
