"""Lot5 runtime integration and complete opt-in chain; real Lua chunks."""
from pathlib import Path
import json
import unittest

from test_hud_crew import _lua, ROOT
from test_hud_alerts_integration import _lua_with_options


class CrewIntegrationTests(unittest.TestCase):
    def test_runtime_mount_update_toggle_rebuild_and_old_manager(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_crew = true
            kyohud.settings.enable_player = false
            kyohud.settings.enable_weapons = false
            kyohud.settings.enable_equipment = false
            panel_double:set_shape(0,0,1920,1080)
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            RT:update(managers.hud,1,.05)
        ''')
        self.assertTrue(lua.eval('kyohud.hud.crew._render_verified'), 'runtime must present crew without manual crew update')
        lua.execute('''
            local C, RT, A = kyohud.hud.crew, kyohud.hud.runtime, kyohud.hud.actors
            local mgr = managers.hud
            _oldroot = C._root
            _token = A:get_crew_snapshot()[1].occupant_token
            kyohud.killstreak = 17
            RT:rebuild(mgr)
            RT:update(mgr,1.6,.05)
            _rebuilt = C._root ~= _oldroot and C:_verify_render()
            _preserved = A:get_crew_snapshot()[1].occupant_token == _token and kyohud.killstreak == 17
            kyohud.settings.enable_crew = false
            RT:refresh_settings(mgr)
            _off = C._root == nil and RT._mounted
            kyohud.settings.enable_crew = true
            RT:refresh_settings(mgr)
            RT:update(mgr,2.2,.05)
            _on = C:_verify_render()
            local other = setmetatable({_safe_script={panel=panel_double},_teammate_panels={}},getmetatable(mgr))
            RT:destroy(other)
            _old_safe = C:_verify_render()
            RT:destroy(mgr)
            _destroyed = C._root == nil and RT._root_panel == nil
        ''')
        for name in ('_rebuilt', '_preserved', '_off', '_on', '_old_safe', '_destroyed'):
            self.assertIs(lua.globals()[name], True, name)

    def test_defaults_persistence_callback_and_menu(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok)
        self.assertIs(lua.eval('kyohud._defaults.enable_crew'), False)
        self.assertIs(lua.eval('kyohud.settings.enable_crew'), False)
        self.assertTrue(lua.eval('type(MenuCallbackHandler.KY_ToggleCrew) == "function"'))
        lua.execute('''
            kyohud.settings.enable_player = false
            kyohud.settings.enable_equipment = true
            _refreshes = 0
            kyohud.hud.runtime.refresh_settings = function() _refreshes = _refreshes + 1 end
            for _, value in ipairs({"on","off"}) do
                MenuCallbackHandler.KY_ToggleCrew(nil,{value=function() return value end})
                local decoded = json.decode(_ky_mem_files[kyohud._settings_path])
                assert(decoded.enable_crew == (value == "on"))
                kyohud.settings.enable_crew = not decoded.enable_crew
                kyohud.Load()
                assert(kyohud.settings.enable_crew == decoded.enable_crew)
            end
            _independent = kyohud.settings.enable_player == false and kyohud.settings.enable_equipment == true
            _ky_mem_files[kyohud._settings_path] = '{"enable_killfeed":true}'
            kyohud.settings.enable_crew = true
            kyohud.Load()
            _migrated = kyohud.settings.enable_crew
        ''')
        self.assertIs(lua.globals()._migrated, False)
        self.assertEqual(lua.globals()._refreshes, 2)
        self.assertIs(lua.globals()._independent, True)
        menu = json.loads((ROOT/'menu/menu.json').read_text(encoding='utf-8-sig'))
        def entries(obj):
            if isinstance(obj, dict):
                yield obj
                for v in obj.values(): yield from entries(v)
            elif isinstance(obj, list):
                for v in obj: yield from entries(v)
        items = [x for x in entries(menu) if x.get('id') == 'ky_enable_crew']
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item['callback'], 'KY_ToggleCrew')
        self.assertEqual(item['value'], 'enable_crew')
        self.assertIs(item['default_value'], False)
        self.assertEqual(item['enabled_by'], 'enable_hud_foundation')
        fallback = (ROOT/'lua/ky_localization.lua').read_text(encoding='utf-8-sig')
        for lang in ('english','french'):
            loc = json.loads((ROOT/f'loc/{lang}.json').read_text(encoding='utf-8-sig'))
            for key in ('ky_opt_enable_crew','ky_opt_enable_crew_desc','ky_hud_crew_ai'):
                self.assertTrue(loc[key])
                self.assertIn(key, fallback)

    def test_manifest_actual_contexts_and_order(self):
        hooks = json.loads((ROOT/'mod.txt').read_text(encoding='utf-8-sig'))['hooks']
        pm = [h['script_path'] for h in hooks if h['hook_id']=='lib/managers/playermanager']
        hud = [h['script_path'] for h in hooks if h['hook_id']=='lib/managers/hudmanagerpd2']
        self.assertEqual(pm.count('lua/hud/actors.lua'),1)
        for path in ('lua/hud/components/crew_card.lua','lua/hud/crew.lua'):
            self.assertEqual(hud.count(path),1)
            self.assertTrue((ROOT/path).is_file())
        self.assertLess(hud.index('lua/hud/actors.lua'),hud.index('lua/hud/crew.lua'))
        self.assertLess(hud.index('lua/hud/components/crew_card.lua'),hud.index('lua/hud/crew.lua'))


if __name__ == '__main__':
    unittest.main()
