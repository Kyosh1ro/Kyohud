import test_hud_assault_states as states
import unittest

BAI_FIXTURE = r'''
BAI = BAI or {}
BAI.EventList = BAI.EventList or {
    AssaultStateChange = "AssaultStateChange",
    AssaultStateChangeOverride = "AssaultStateChangeOverride"
}
BAI.Events = BAI.Events or {}
BAI.BAIHost = true
BAI.settings = BAI.settings or {show_assault_states = true}
BAI.advanced = false
function BAI:AddEvent(event, callback, unused, priority, id)
    if not self.Events[event] then self.Events[event] = {} end
    table.insert(self.Events[event], {callback=callback, priority=priority, id=id})
    return true
end
function BAI:CallEvent(event, ...)
    local cbs = self.Events[event]
    if not cbs then return end
    for _, entry in ipairs(cbs) do
        entry.callback(...)
    end
end
function BAI:GetOption(name)
    return self.settings[name]
end
function BAI:ShowAdvancedAssaultInfo()
    return self.advanced == true
end
'''

class BAIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.helper = states.AssaultMultiStateLabelTests()

    def _inject_bai(self, lua, bai_host=True, advanced=False, show_states=True):
        lua.execute(BAI_FIXTURE)
        lua.execute(f'''
            BAI.BAIHost = {str(bai_host).lower()}
            BAI.advanced = {str(advanced).lower()}
            BAI.settings.show_assault_states = {str(show_states).lower()}
        ''')

    def test_bai_add_event_once(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua)

        lua.execute('''
            _count_before = 0
            for k, v in pairs(BAI.Events) do _count_before = _count_before + #v end
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.05)
            _count_after1 = 0
            for k, v in pairs(BAI.Events) do _count_after1 = _count_after1 + #v end
            A:update(managers.hud, 2.6, 0.5)
            _count_after2 = 0
            for k, v in pairs(BAI.Events) do _count_after2 = _count_after2 + #v end
        ''')

        g = lua.globals()
        self.assertGreater(g._count_after1, 0, "Must register callbacks")
        self.assertEqual(g._count_after2, g._count_after1, "Must not duplicate")

    def test_bai_callevent_sustain_label(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua)

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.05)
            BAI:CallEvent("AssaultStateChange", "sustain", true)
            A:update(managers.hud, 2.1, 0.05)
            _label = A:_resolve_status_label()
        ''')

        g = lua.globals()
        self.assertEqual(str(g._label), "MAINTIEN")

    def test_bai_host_false_keeps_assault(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua, bai_host=False)

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 1.5, 0.05)
            BAI:CallEvent("AssaultStateChange", "sustain", true)
            A:update(managers.hud, 2.0, 0.05)
            _label = A:_resolve_status_label()
        ''')

        g = lua.globals()
        self.assertEqual(str(g._label), "ASSAULT")

    def test_bai_advanced_retreat(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua, bai_host=True, advanced=False)

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 1.5, 0.05)
            _root_before = A._root_panel:visible()
            _native_before = A._native_acquired
            _settings_before = BAI.settings.show_assault_states
            _count_before = 0
            for k, v in pairs(BAI.Events) do _count_before = _count_before + #v end
            BAI.advanced = true
            A:update(managers.hud, 2.0, 0.5)
            _root_after = A._root_panel:visible()
            _native_after = A._native_acquired
            _settings_after = BAI.settings.show_assault_states
            _count_after = 0
            for k, v in pairs(BAI.Events) do _count_after = _count_after + #v end
        ''')

        g = lua.globals()
        self.assertTrue(bool(g._root_before))
        self.assertTrue(bool(g._native_before))
        self.assertFalse(bool(g._root_after), "Root must be hidden")
        self.assertFalse(bool(g._native_after), "native_acquired must be false")
        self.assertEqual(g._settings_after, g._settings_before)
        self.assertEqual(g._count_after, g._count_before)

    def test_bai_replaced_old_callback_inert(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua)

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 1.5, 0.05)
            _old_bai = BAI

            BAI = {}
            BAI.EventList = {
                AssaultStateChange = "AssaultStateChange",
                AssaultStateChangeOverride = "AssaultStateChangeOverride"
            }
            BAI.Events = {}
            BAI.BAIHost = true
            BAI.settings = {show_assault_states = true}
            BAI.advanced = false
            function BAI:AddEvent(event, callback, unused, priority, id)
                if not self.Events[event] then self.Events[event] = {} end
                table.insert(self.Events[event], {callback=callback, priority=priority, id=id})
                return true
            end
            function BAI:CallEvent(event, ...)
                local cbs = self.Events[event]
                if not cbs then return end
                for _, entry in ipairs(cbs) do entry.callback(...) end
            end
            function BAI:GetOption(name) return self.settings[name] end
            function BAI:ShowAdvancedAssaultInfo() return self.advanced == true end

            A:update(managers.hud, 2.0, 0.5)

            _old_bai:CallEvent("AssaultStateChange", "sustain", true)
            A:update(managers.hud, 2.1, 0.05)
            _label_old = A:_resolve_status_label()

            BAI:CallEvent("AssaultStateChange", "fade", true)
            A:update(managers.hud, 2.2, 0.05)
            _label_new = A:_resolve_status_label()
        ''')

        g = lua.globals()
        self.assertEqual(str(g._label_old), "ASSAULT",
            "Old BAI callback must be inert after replacement")
        self.assertEqual(str(g._label_new), "RETRAIT",
            "New BAI callback must work after replacement")

    def test_bai_option_false(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua, bai_host=True, show_states=False)

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 1.5, 0.05)
            BAI:CallEvent("AssaultStateChange", "sustain", true)
            A:update(managers.hud, 2.0, 0.05)
            _label = A:_resolve_status_label()
        ''')

        g = lua.globals()
        self.assertEqual(str(g._label), "ASSAULT",
            "BAI bonus must not apply when show_assault_states is false")

    def test_bai_source_replaced_callback_inert(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua)

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 1.5, 0.05)
            BAI:CallEvent("AssaultStateChange", "sustain", true)
            A:update(managers.hud, 1.6, 0.05)
            _label_before = A:_resolve_status_label()

            managers.groupai._state = GroupAIState:new()
            managers.groupai._state._is_server = false
            managers.groupai._state._assault_mode = false
            managers.groupai._state._task_data = {assault = {active = false}}
            managers.groupai._state._hostage_count = 0
            managers.groupai._state._converted = {}

            A:update(managers.hud, 2.1, 0.05)
            A:update(managers.hud, 2.6, 0.05)
            _label_t2_1 = A:_resolve_status_label()
            _bonus_t2_1 = A._bai_bonus_phase

            BAI:CallEvent("AssaultStateChange", "fade", true)
            A:update(managers.hud, 2.7, 0.05)
            _label_after = A:_resolve_status_label()
        ''')

        g = lua.globals()
        self.assertEqual(str(g._label_before), "MAINTIEN")
        self.assertEqual(str(g._label_t2_1), "ASSAULT",
            "Source replacement + updates must yield ASSAULT, got "
            + str(g._label_t2_1))
        self.assertIsNone(g._bonus_t2_1,
            "bonus phase must be nil after source replacement, got "
            + str(g._bonus_t2_1))
        self.assertEqual(str(g._label_after), "ASSAULT",
            "Old BAI callback must be inert after source replacement, got "
            + str(g._label_after))

    def test_bai_advanced_qualification(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua, bai_host=False, show_states=False, advanced=True)

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 1.5, 0.05)
            A:update(managers.hud, 2.0, 0.5)
            _root_vis = A._root_panel:visible()
            _native = A._native_acquired
            _qualified = A._bai_qualified
            _advanced = A._bai_advanced_active
        ''')

        g = lua.globals()
        self.assertFalse(bool(g._root_vis),
            "Root must be hidden when BAIHost=false and show_states=false")
        self.assertFalse(bool(g._native),
            "native_acquired must be false when BAIHost=false")
        self.assertFalse(bool(g._qualified),
            "BAI must not be qualified without BAIHost/show_states")
        self.assertTrue(bool(g._advanced),
            "Advanced must be true when BAI.advanced=true regardless of qualification")

    def test_bai_advanced_getter_throw_fallback(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua, bai_host=True, show_states=True, advanced=False)

        lua.execute('''
            function BAI:ShowAdvancedAssaultInfo()
                error("intentional throw")
            end
            local A = kyohud.hud.assault
            A:update(managers.hud, 1.5, 0.05)
            A:update(managers.hud, 2.0, 0.5)
            _root_throw = A._root_panel:visible()
            _native_throw = A._native_acquired

            BAI.ShowAdvancedAssaultInfo = nil
            A:update(managers.hud, 2.5, 0.5)
            _root_missing = A._root_panel:visible()
            _native_missing = A._native_acquired
        ''')

        g = lua.globals()
        self.assertFalse(bool(g._root_throw),
            "Root must remain hidden when getter throws")
        self.assertFalse(bool(g._native_throw),
            "native_acquired must remain false when getter throws")
        self.assertFalse(bool(g._root_missing),
            "Root must remain hidden when getter missing")
        self.assertFalse(bool(g._native_missing),
            "native_acquired must remain false when getter missing")

    def test_bai_rebuild_no_double_subscription(self):
        lua, ok = self.helper._make_lua(False, "sustain", False, True, False, True)
        self.assertTrue(ok)
        self._inject_bai(lua)

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 1.5, 0.05)
            A:update(managers.hud, 2.0, 0.5)
            _count_before = 0
            for k, v in pairs(BAI.Events) do
                _count_before = _count_before + #v
            end

            A:rebuild(managers.hud)
            A:update(managers.hud, 2.5, 0.5)
            A:update(managers.hud, 3.0, 0.5)
            _count_after = 0
            for k, v in pairs(BAI.Events) do
                _count_after = _count_after + #v
            end
        ''')

        g = lua.globals()
        self.assertGreater(g._count_before, 0,
            "Callbacks must be registered before rebuild")
        self.assertEqual(g._count_after, g._count_before,
            "Rebuild must not duplicate BAI event subscriptions")


if __name__ == "__main__":
    unittest.main()
